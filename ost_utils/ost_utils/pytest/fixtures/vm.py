#
# Copyright 2020 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

import netaddr.core
import netaddr.ip

import pytest

from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.sdk import *


@pytest.fixture(scope="session")
def get_hosts_hostname_for_vm(hosts_service, get_vm_service_for_vm):

    def hostname_for(vm_name):
        vm_service = get_vm_service_for_vm(vm_name)
        host_id = vm_service.get().host.id
        hosts = hosts_service.list(search='id={}'.format(host_id))
        if len(hosts) != 1:
            raise RuntimeError(
                "Could not find host for vm: {}".format(vm_name)
            )
        return hosts[0].name

    return hostname_for


@pytest.fixture(scope="session")
def get_ansible_host_for_vm(ansible_by_hostname, get_hosts_hostname_for_vm):

    def ansible_host_for(vm_name):
        return ansible_by_hostname(get_hosts_hostname_for_vm(vm_name))

    return ansible_host_for


@pytest.fixture(scope="session")
def get_vm_ip(get_ansible_host_for_vm):

    def get_ip(vm_name_or_ip):
        try:
            netaddr.ip.IPAddress(vm_name_or_ip)
            return vm_name_or_ip
        except netaddr.core.AddrFormatError:
            ansible_host = get_ansible_host_for_vm(vm_name_or_ip)
            ret = ansible_host.shell('dig +short {}'.format(vm_name_or_ip))
            return ret["stdout"].strip()

    return get_ip


@pytest.fixture(scope="session")
def get_vm_libvirt_xml(get_ansible_host_for_vm):

    def get_xml(vm_name):
        ansible_host = get_ansible_host_for_vm(vm_name)
        ret = ansible_host.shell('virsh -r dumpxml {}'.format(vm_name))
        return ret['stdout'].strip()

    return get_xml
