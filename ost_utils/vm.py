#!/usr/bin/python

from sh import vagrant
from sh import scp
from sh import virsh

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


def check_running(func):
    wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.running():
            raise "Error: " + self.name
        return func(self, *args, **kwargs)

    return wrapper

def sh_output_result(func):
    @wraps(func)
    def func_wrapper(*args,**kwargs):
        try:
            ret = func(*args,**kwargs)
        except ErrorReturnCode as e:
            ret = e
        result = CommandStatus( ret.stdout, ret.stderr, ret.exit_code)
        return result
    return func_wrapper

_CommandStatus = collections.namedtuple(
    'CommandStatus', ('out', 'err', 'code')
)

class CommandStatus(_CommandStatus):
    def __nonzero__(self):
        return self.code

class VagrantHosts(object):

    def __init__(self):
        self._engine_vm = ""
        self._engine_vms = []
        self._host_vms = []
        self._vms = []
        self._prefix = ""
        self._virt_env = ""
        self.collect_vms()

    # we add this functionality in order not to change
    # the tests
    def __getattr__(self,name):
        if name == 'virt_env':
            return self
        raise AttributeError(name)

    def collect_vms(self):
        host_list = []
        """Return the status of the vagrant machine."""
        out = vagrant("status")
        #all_hosts_statuses = re.findall(r"^\S+\s+[shutoff|running]+\s+\(+libvirt+\)+\s+", out, re.MULTILINE)
        all_hosts_statuses = re.findall(r"^\S+\s+\S+\s+\(+libvirt+\)+\s+", out.stdout, re.MULTILINE)
        for host_status in all_hosts_statuses:
            words = re.split('\s+', host_status)
            host_list.append(VM(words[0]))
            if "engine" in words[0]:
                self._engine_vm = VM(words[0])
            if "host" in words[0]:
                self._host_vms.append(VM(words[0]))
        self._vms = host_list

    def engine_vm(self):
        return self._engine_vm

    ## for multiple engine
    def engine_vms(self):
        return self._engine_vm[:]

    def host_vms(self):
        return self._host_vms[:]

    def vms(self):
        return self._vms[:]

    def set_prefix(self):
        if os.getenv("VAGRANT_CWD"):
            self._prefix = os.getenv("VAGRANT_CWD")
        if self._prefix == "None":
            self._prefix = ""
            vagrant_dir = os.getcwd() + "/.vagrant"
            if os.path.exists(vagrant_dir):
                self._prefix = os.getcwd()

    def get_prefix(self):
        return self._prefix

class VM(object):

    def __init__(self, hostname):
        self._hostname = hostname
        host_config = self.parse_ssh_config(self._hostname)
        self._ip =  host_config["hostname"]
        self._identityfile = host_config["identityfile"][0]
        self._config_file_path = os.path.dirname(host_config["identityfile"][0])

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


    def ip(self):
        return self._ip

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
    def copy_to(self, local_path, remote_path, recursive=True, as_user='vagrant'):
        recursive_param = ''

        if recursive:
            recursive_param ='-r'

        command = ['-i', str(self._identityfile), '-o',  'StrictHostKeyChecking=no','-o',
            'UserKnownHostsFile=/dev/null' ,  str(local_path),
            str(as_user) + "@" + str(self._ip) + ":" + str(remote_path)]
        print " ".join(command)
        ret = scp(command)
        return ret

    @sh_output_result
    def copy_from(self, remote_path, local_path, recursive=True, as_user='vagrant'):
        recursive_param = ''

        if recursive:
            recursive_param ='-r'
        command = ['-i', str(self._identityfile), '-o',  'StrictHostKeyChecking=no', '-o',
            'UserKnownHostsFile=/dev/null', recursive_param,
            str(as_user) + "@" + str(self._ip) + ":" + str(remote_path), str(local_path)]
        print " ".join(command)
        ret = scp(command)
        return ret

    def nic(self):
        return self._ip

    @sh_output_result
    def nets(self):
        """Return vagrant machine network cards."""
        command = ['-c', 'qemu:///system', 'domifaddr', self._domain_uuid]
        ret = virsh(command)
        return ret

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

def main():

    print "VAGRANT"
    v = VagrantHosts()
    v.collect_vms()
    print v.vms()
    #v.set_prefix()
    print v.get_prefix()
    #print "Host"
    print v.host_vms()
    #print "Engine"
    print v.engine_vms()

    vm = VM('engine')
    ret = vm.copy_to('/tmp/ost_utils/ost.py', '/tmp' , recursive=True, as_user='root')
    print ret.code
    print ret.out
    print ret.err
    print 'ip: ' + vm.nic()
    from pprint import pprint
    pprint(vars(vm))
    #print vm.nets()
    print vm.running()
    print vm.service('ovirt-engine').alive()
    print vm.service('ovirt-engine')._request_start()
    print vm.service('ovirt-enginex')._request_start()

if __name__ == "__main__":
    main()
