#!/usr/bin/python

from sh import vagrant
from sh import scp
from sh import virsh

from sh import ErrorReturnCode
from sh import CommandNotFound
import paramiko
import subprocess
import os
import sys
import re


class VagrantHosts(object):

    def __init__(self):
        self._engine_vm = ""
        self._engine_vms = []
        self._host_vms = []
        self._vms = []
        self._prefix = ""
        self._virt_env = ""

    def collect_vms(self):
        host_list = []
        """Return the status of the vagrant machine."""
        out = vagrant("status")
        #all_hosts_statuses = re.findall(r"^\S+\s+[shutoff|running]+\s+\(+libvirt+\)+\s+", out, re.MULTILINE)
        all_hosts_statuses = re.findall(r"^\S+\s+\S+\s+\(+libvirt+\)+\s+", out.stdout, re.MULTILINE)
        for host_status in all_hosts_statuses:
            words = re.split('\s+', host_status)
            host_list.append(words[0])
            if "engine" in words[0]:
                self._engine_vm = words[0]
            if "host" in words[0]:
                self._host_vms.append(words[0])
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

        ssh_config = self.info()
        conf = paramiko.SSHConfig()
        conf.parse(ssh_config)
        host_config = conf.lookup(self._hostname)
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

    def get_params(self, name):
        return getattr(self, name)

    def ssh(self, command, as_user=None):
        if as_user:
            command = ['sudo', '-u', as_user] + command
        ret = vagrant.ssh(self._hostname, '-c', ' '.join(command))
        return ret

    def status(self):
        """Return vagrant machine status."""
        ret = vagrant.status(self._hostname)
        return ret

    def info(self):
        """Return vagrant machine status."""
        ret = vagrant("ssh-config",self._hostname)
        return ret

    def global_status(self):
        """Return vagrant machine status."""
        ret = vagrant("global-status")
        return ret

    def copy_to(self, local_path, remote_path, recursive=True, as_user='vagrant'):
        recursive_param = ''
        ssh_config = self.info()
        conf = paramiko.SSHConfig()
        conf.parse(ssh_config)
        host_config = conf.lookup(self._hostname)

        ip =  host_config["hostname"]
        identityfile = str(host_config["identityfile"][0])

        if recursive:
            recursive_param ='-r'

        command = ['-i', str(identityfile), '-o',  'StrictHostKeyChecking=no','-o', 'UserKnownHostsFile=/dev/null' ,  str(local_path), str(as_user) + "@" + str(host_config["hostname"]) + ":" + str(remote_path)]
        print " ".join(command)
        ret = scp(command)
        return ret


    def copy_from(self, remote_path, local_path, recursive=True, as_user='vagrant'):
        recursive_param = ''
        ssh_config = self.info()
        conf = paramiko.SSHConfig()
        conf.parse(ssh_config)
        host_config = conf.lookup(self._hostname)

        ip =  host_config["hostname"]
        identityfile = str(host_config["identityfile"][0])

        if recursive:
            recursive_param ='-r'
        command = ['-i', str(identityfile), '-o',  'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', recursive_param, str(as_user) + "@" + str(host_config["hostname"]) + ":" + str(remote_path), str(local_path)]
        print " ".join(command)
        ret = scp(command)
        return ret

    def nic(self):
        ssh_config = self.info()
        #ssh_config = vagrant("ssh-config",self._hostname)
        conf = paramiko.SSHConfig()
        conf.parse(ssh_config)
        host_config = conf.lookup(self._hostname)

        return host_config["hostname"]

    def nets(self):
        """Return vagrant machine network cards."""
        command = ['-c', 'qemu:///system', 'domifaddr', self._domain_uuid]
        ret = virsh(command)
        return ret

    def destroy(self):
        """Destroy the vagrant machine."""
        ret = vagrant.destroy(self._hostname, '-f')
        return ret

    def halt(self):
        """Halt the vagrant machine."""
        ret = vagrant.halt(self._hostname, '-f')
        return ret

    def up(self):
        """Start the vagrant machine."""
        ret = vagrant.up(self._hostname)
        return ret

    def suspend(self):
        """Suspend the vagrant machine."""
        ret = vagrant.suspend(self._hostname)
        return ret

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
    vm.copy_to('/tmp/ost_utils/ost.py', '/tmp' , recursive=True, as_user='root')
    print 'ip: ' + vm.nic()
    from pprint import pprint
    pprint(vars(vm))
    #print vm.nets()

if __name__ == "__main__":
    main()
