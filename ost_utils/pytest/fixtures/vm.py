#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import ipaddress

import pytest

from ost_utils.pytest.fixtures.sdk import *


@pytest.fixture(scope="session")
def get_hosts_hostname_for_vm(hosts_service, get_vm_service_for_vm):
    def hostname_for(vm_name):
        vm_service = get_vm_service_for_vm(vm_name)
        host_id = vm_service.get().host.id
        hosts = hosts_service.list(search=f'id={host_id}')
        if len(hosts) != 1:
            raise RuntimeError(f"Could not find host for vm: {vm_name}")
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
            ipaddress.ip_address(vm_name_or_ip)
            return vm_name_or_ip
        except ValueError:
            ansible_host = get_ansible_host_for_vm(vm_name_or_ip)
            ret = ansible_host.shell(f'dig +short {vm_name_or_ip}')
            return ret["stdout"].strip()

    return get_ip


@pytest.fixture(scope="session")
def get_vm_libvirt_xml(get_ansible_host_for_vm):
    def get_xml(vm_name):
        ansible_host = get_ansible_host_for_vm(vm_name)
        ret = ansible_host.shell(f'virsh -r dumpxml {vm_name}')
        return ret['stdout'].strip()

    return get_xml
