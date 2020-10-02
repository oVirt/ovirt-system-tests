#!/usr/bin/python

from __future__ import print_function

from sh import vagrant
from sh import scp
from sh import virsh
from sh import grep

from sh import ErrorReturnCode
from sh import CommandNotFound
from sh import RunningCommand

import paramiko
import subprocess
import os
import sys
import re
from functools import wraps
import collections
import io
import service
import time
import warnings
import logging
import yaml
from itertools import chain
from collections import OrderedDict
import testlib
from ost_utils.command_status import CommandStatus
from ost_utils.sdk_utils import available_sdks, require_sdk
from ost_utils.log_utils import LevelFilter

import ovirtsdk.api
from ovirtsdk.infrastructure.errors import (RequestError, ConnectionError)
import utils

try:
    import ovirtsdk4 as sdk4
    import ovirtsdk4.types as otypes
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)
# sh is bombing the log, handle it.
logging.getLogger('sh.command').addFilter(LevelFilter(logging.WARNING))


def check_running(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.running():
            raise "Error: " + self.name
        return func(self, *args, **kwargs)

    return wrapper


def sh_output_result(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except ErrorReturnCode as e:
            ret = e
        result = CommandStatus(ret.stdout, ret.stderr, ret.exit_code)
        return result
    return func_wrapper


class VagrantHosts(object):

    def __init__(self):
        self._vms = {}
        self._engine_vms = []
        self._host_vms = []
        self._prefix_path = None
        self._set_prefix_path()
        self.collect_vms()

    # we add this functionality in order not to change
    # the tests
    def __getattr__(self, name):
        if name == 'virt_env':
            return self
        raise AttributeError(name)

    def collect_vms(self):
        """Return the status of the vagrant machine."""
        domains_dir = os.path.join(self.prefix_path, 'machines')
        LOGGER.debug('Loading domain from ' + domains_dir)
        _, domains, _ = next(os.walk(domains_dir))
        if not domains:
            raise RuntimeError('Vagrant env does not have any domain')

        for domain in domains:
            self._vms[domain] = VM(domain)
            if "engine" in domain:
                self._engine_vms.append(EngineVM(domain))
            elif "host" in domain:
                self._host_vms.append(HostVM(domain))

    def engine_vm(self):
        return self._engine_vms[0]

    def engine_vms(self):
        return self._engine_vms[:]

    def host_vms(self):
        return self._host_vms[:]

    def vms(self):
        return self._vms[:]

    def get_vm(self, name):
        for x in chain(self.host_vms(), self.engine_vms()):
            suffix = x.name()
            LOGGER.debug('Suffix ' + suffix)
            if name.endswith(suffix):
                return x

    def get_vms(self, vm_names=None):
        if vm_names is None:
            vm_names = self._vms.keys()
        missing_vms = []
        vms = {}
        for name in vm_names:
            try:
                vms[name] = self._vms[name]
            except KeyError:
                # TODO: add resolver by suffix
                missing_vms.append(name)

        if missing_vms:
            raise utils.OSTUserException(
                'The following vms do not exist: \n{}'.format(
                    '\n'.join(missing_vms)
                )
            )

        return vms

    def _set_prefix_path(self):
        for base in (os.getenv("VAGRANT_CWD"), os.curdir):
            possible_prefix_path = os.path.join(base, '.vagrant')
            if os.path.isdir(possible_prefix_path):
                self._prefix_path = possible_prefix_path
                break
        else:
            raise RuntimeError(
                'Failed to locate Vagarnt env.'
                ' VAGRANT_CWD is not set and ./vagrant does not exists'
            )


    @property
    def prefix_path(self):
        return self._prefix_path


class VM(object):

    def __init__(self, hostname):
        self._hostname = hostname
        host_config = self.parse_ssh_config(self._hostname)
        self._ip =  host_config["hostname"]
        self._identityfile = host_config["identityfile"][0]
        self._config_file_path = os.path.dirname(host_config["identityfile"][0])
        self._root_password = 'vagrant'
        ### we assume that the files are located in a specific location according to libvirt
        ### vagrant, we don't have api for that
        ### vagrant plugin vagrant-libvirt (0.0.45, global)
        with open(self._config_file_path + '/id', 'r') as myfile:
            self._domain_uuid = myfile.read()
        with open(self._config_file_path + '/vagrant_cwd', 'r') as myfile:
            self._vagrant_cwd = myfile.read()
        with open(self._config_file_path + '/box_meta', 'r') as myfile:
            self._box_meta_data = myfile.read()
        self._service_class = service.SystemdService
        self._nics = self.nics()

    def ip(self):
        return self._ip

    def name(self):
        return self._hostname

    def root_password(self):
        return self._root_password

    def get_params(self, name):
        return getattr(self, name)

    def parse_ssh_config(self, hostname):
        buf = io.StringIO()
        ssh_config = self.info()
        conf = paramiko.SSHConfig()
        buf = io.StringIO(unicode(ssh_config.out, 'unicode-escape'))
        buf.seek(0)
        conf.parse(buf)
        buf.close()
        return conf.lookup(hostname)

    def service(self, name):
        return self._service_class(self, name)

    def running(self):
        ret = self.status()
        host_status = re.findall(r"^\S+\s+running+\s+\(+libvirt+\)+\s+", ret.out, re.MULTILINE)
        if host_status:
            return True
        else:
            return False

    @sh_output_result
    def ssh(self, command, as_user='root'):
        if as_user:
            command = ['sudo', '-u', as_user] + command
        ret = vagrant.ssh(self._hostname, '-c', ' '.join(command))
        return ret

    @sh_output_result
    def status(self):
        """Return vagrant machine status."""
        ret = vagrant.status(self._hostname)
        return ret

    @sh_output_result
    def info(self):
        """Return vagrant machine status."""
        ret = vagrant("ssh-config",self._hostname)
        return ret

    @sh_output_result
    def global_status(self):
        """Return vagrant machine status."""
        ret = vagrant("global-status")
        return ret

    @sh_output_result
    def copy_to(self, local_path, remote_path, recursive=True, as_user='root'):
        recursive_param = ''

        if recursive:
            recursive_param ='-r'

        command = ['-i', str(self._identityfile), '-o',  'StrictHostKeyChecking=no','-o',
            'UserKnownHostsFile=/dev/null', recursive_param, str(local_path),
            str(as_user) + "@" + str(self._ip) + ":" + str(remote_path)]
        print(" ".join(command))
        ret = scp(command)
        return ret

    @sh_output_result
    def copy_from(self, remote_path, local_path, recursive=True, as_user='root'):
        recursive_param = ''

        if recursive:
            recursive_param ='-r'
        command = ['-i', str(self._identityfile), '-o',  'StrictHostKeyChecking=no', '-o',
            'UserKnownHostsFile=/dev/null', recursive_param,
            str(as_user) + "@" + str(self._ip) + ":" + str(remote_path), str(local_path)]
        print(" ".join(command))
        ret = scp(command)
        return ret

    def nic(self):
        return self._ip

    def all_ips(self):
        ips = self.nets().out.split('\n')
        ips = [x for x in ips if x != '']
        return ips

    @sh_output_result
    def get_virsh_nics(self):
        command = ['-c', 'qemu:///system', 'domiflist', self._domain_uuid ]
        ret = virsh(command)
        return ret

    def nics(self):
        nics = self.get_virsh_nics()
        pattern = os.path.basename(os.environ.get('SUITE')).replace("-", "_") + '-net-\w*'
        match = re.findall(pattern,nics.out)
        return match

    @sh_output_result
    def nets(self):
        """Return vagrant machine network cards."""
        command = ['-c', 'qemu:///system', 'domifaddr', self._domain_uuid ]
        grep_cmd = ['-oE' ,'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' ]
        ret = grep(virsh(command),grep_cmd)
        return ret

    @sh_output_result
    def get_ips_in_net(self, net_name):
        """Return ip in network."""
        command = ['-c', 'qemu:///system', 'net-dhcp-leases', net_name ]
        grep_cmd = ['-w' ,self.name() ]
        ret = grep(virsh(command),grep_cmd)
        return ret

    def ips_in_net(self, net_name):
        """Return list ips in network."""
        ips_in_net = self.get_ips_in_net(net_name)
        pattern = '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
        match = re.findall(pattern,ips_in_net.out)
        return match

    @sh_output_result
    def destroy(self):
        """Destroy the vagrant machine."""
        ret = vagrant.destroy(self._hostname, '-f')
        return ret

    @sh_output_result
    def halt(self):
        """Halt the vagrant machine."""
        ret = vagrant.halt(self._hostname, '-f')
        return ret

    @sh_output_result
    def up(self):
        """Start the vagrant machine."""
        ret = vagrant.up(self._hostname)
        return ret

    @sh_output_result
    def suspend(self):
        """Suspend the vagrant machine."""
        ret = vagrant.suspend(self._hostname)
        return ret

    @sh_output_result
    def resume(self):
        """Resume the vagrant machine."""
        ret = vagrant.resume(self._hostname)
        return ret


class EngineVM(VM):
    def __init__(self, *args, **kwargs):
        super(EngineVM, self).__init__(*args, **kwargs)
        self._username = kwargs.get('ovirt-engine-user', 'admin@internal')
        self._password = str(kwargs.get('ovirt-engine-password', u'123'))
        self._api_v3 = None
        self._api_v4 = None
        self._metadata = {}
        self._metadata['ovirt-engine-password'] = self._password

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def metadata(self):
        return self._metadata

    def _create_api(self, api_ver):
        url = 'https://%s/ovirt-engine/api' % self.ip()
        if api_ver == 3:
            if '3' not in available_sdks():
                raise RuntimeError('oVirt Python SDK v3 not found.')
            return ovirtsdk.api.API(
                url=url.encode('ascii'),
                username=self.username,
                password=self.password.encode('ascii'),
                validate_cert_chain=False,
                insecure=True,
            )
        if api_ver == 4:
            import logging
            logging.basicConfig(level=logging.DEBUG,filename='/tmp/x.log')
            if '4' not in available_sdks():
                raise RuntimeError('oVirt Python SDK v4 not found.')
            return sdk4.Connection(
                url= url.encode('ascii'),
                username=self.username,
                password=self.password.encode('ascii'),
                insecure=True,
                debug=True,
            )
        raise RuntimeError('Unknown API requested: %s' % api_ver)

    def _get_api(self, api_ver):
        try:
            api_v3 = []
            api_v4 = []

            def get():
                instance = self._create_api(api_ver)
                if instance:
                    if api_ver == 3:
                        api_v3.append(instance)
                    else:
                        api_v4.append(instance)
                    return True
                return False

            testlib.assert_true_within_short(
                get,
                allowed_exceptions=[RequestError, ConnectionError],
            )
        except AssertionError:
            raise RuntimeError('Failed to connect to the engine')
        if api_ver == 3:
            return api_v3.pop()
        else:
            testapi = api_v4.pop()
            counter = 1
            while not testapi.test():
                if counter == 20:
                    raise RuntimeError('test api call failed')
                else:
                    time.sleep(3)
                    counter += 1

            return testapi

    def get_api(self, api_ver=3):
        if api_ver == 3:
            return self.get_api_v3()
        if api_ver == 4:
            return self.get_api_v4()

    def get_api_v3(self):
        if self._api_v3 is None or not self._api_v3.test():
            self._api_v3 = self._get_api(api_ver=3)
        return self._api_v3

    def get_api_v4(self, check=False):
        if self._api_v4 is None or not self._api_v4.test():
            self._api_v4 = self._get_api(api_ver=4)
            if check and self._api_v4 is None:
                raise RuntimeError('Could not connect to engine')
        return self._api_v4

    def get_api_v4_system_service(self):
        api = self.get_api_v4(False)
        return api.system_service()

    @require_sdk(version='4')
    def status(self):
        api = self.get_api_v4(check=True)
        sys_service = api.system_service().get()
        info = {'global': {}, 'items': {}}

        info['global']['version'] = \
            sys_service.product_info.version.full_version
        info['global']['web_ui'] = OrderedDict(
            [
                ('url', self.ip()),
                ('username', self.username),
                ('password', self.password),
            ]
        )

        for k, v in vars(sys_service.summary).viewitems():
            if isinstance(v, otypes.ApiSummaryItem):
                info['items'][k.lstrip('_')] = OrderedDict(
                    [
                        ('total', v.total),
                        ('active', v.active),
                    ]
                )

        return info


class HostVM(VM):
    pass

class HEHostVM(HostVM):
    pass
