#
# Copyright 2016-2021 Red Hat, Inc.
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
from __future__ import absolute_import
from __future__ import print_function

import ipaddress
import logging

from ovirtsdk4.types import Host, NetworkUsage, VmStatus, Cluster, MigrationOptions, MigrationPolicy
import json

import pytest
import test_utils
from test_utils import network_utils_v4, assert_finished_within_long
from ost_utils import assertions


DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

NIC_NAME = 'eth0'
VLAN200_IF_NAME = '{}.200'.format(NIC_NAME)

DEFAULT_MTU = 1500

LOGGER = logging.getLogger(__name__)

MIGRATION_NETWORK = 'Migration_Net'
MIGRATION_NETWORK_IPv4_ADDR = '192.0.3.{}'
MIGRATION_NETWORK_IPv4_MASK = '255.255.255.0'
MIGRATION_NETWORK_IPv6_ADDR = '1001:0db8:85a3:0000:0000:574c:14ea:0a0{}'
MIGRATION_NETWORK_IPv6_MASK = '64'

VM0_NAME = 'vm0'

# Migration policy UUIDs are hard-coded
MIGRATION_POLICY_POSTCOPY='a7aeedb2-8d66-4e51-bb22-32595027ce71'


@pytest.fixture(scope="session")
def system_service(engine_api):
    return engine_api.system_service()


@pytest.fixture(scope="session")
def all_hosts_hostnames(system_service):
    hosts_service = system_service.hosts_service()
    return {host.name for host in hosts_service.list()}


@pytest.fixture(scope="module")
def prepare_migration_vlan(system_service):
    assert network_utils_v4.set_network_usages_in_cluster(
        system_service, MIGRATION_NETWORK, CLUSTER_NAME, [NetworkUsage.MIGRATION])

    # Set Migration_Network's MTU to match the other VLAN's on the NIC.
    assert network_utils_v4.set_network_mtu(
        system_service, MIGRATION_NETWORK, DC_NAME, DEFAULT_MTU)


def migrate_vm(all_hosts_hostnames, ansible_by_hostname, system_service):
    vm_service = test_utils.get_vm_service(system_service, VM0_NAME)
    vm_id = vm_service.get().id
    hosts_service = system_service.hosts_service()

    def _current_running_host():
        host_id = vm_service.get().host.id
        host = hosts_service.list(
            search='id={}'.format(host_id))[0]
        return host.name

    src_host = _current_running_host()
    dst_host = next(iter(all_hosts_hostnames - {src_host}))

    LOGGER.debug('source host: {}'.format(src_host))
    LOGGER.debug('destination host: {}'.format(dst_host))

    assert_finished_within_long(
        vm_service.migrate,
        system_service,
        host=Host(name=dst_host)
    )

    # Verify that VDSM cleaned the vm in the source host
    def vm_is_not_on_host():
        ansible_src_host = ansible_by_hostname(src_host)
        out = ansible_src_host.shell('vdsm-client Host getVMList')["stdout"]
        vms = json.loads(out)
        return vm_id not in [vm["vmId"] for vm in vms]

    assertions.assert_true_within_short(vm_is_not_on_host)

    assertions.assert_true_within_short(
        lambda: vm_service.get().status == VmStatus.UP
    )

    assert _current_running_host() == dst_host


def prepare_migration_attachments_ipv4(system_service):
    hosts_service = system_service.hosts_service()

    for index, host in enumerate(
            test_utils.hosts_in_cluster_v4(system_service, CLUSTER_NAME),
            start=1):
        host_service = hosts_service.host_service(id=host.id)

        ip_address = MIGRATION_NETWORK_IPv4_ADDR.format(index)

        ip_configuration = network_utils_v4.create_static_ip_configuration(
            ipv4_addr=ip_address,
            ipv4_mask=MIGRATION_NETWORK_IPv4_MASK)

        network_utils_v4.attach_network_to_host(
            host_service, NIC_NAME, MIGRATION_NETWORK, ip_configuration)

        actual_address = next(nic for nic in host_service.nics_service().list()
                              if nic.name == VLAN200_IF_NAME).ip.address
        assert (
            ipaddress.ip_address(actual_address) ==
            ipaddress.ip_address(ip_address)
        )


def prepare_migration_attachments_ipv6(system_service):
    hosts_service = system_service.hosts_service()

    for index, host in enumerate(
            test_utils.hosts_in_cluster_v4(system_service, CLUSTER_NAME),
            start=1):
        host_service = hosts_service.host_service(id=host.id)

        ip_address = MIGRATION_NETWORK_IPv6_ADDR.format(index)

        ip_configuration = network_utils_v4.create_static_ip_configuration(
            ipv6_addr=ip_address,
            ipv6_mask=MIGRATION_NETWORK_IPv6_MASK)

        network_utils_v4.modify_ip_config(
            system_service, host_service, MIGRATION_NETWORK, ip_configuration)

        actual_address = next(nic for nic in host_service.nics_service().list()
                              if nic.name == VLAN200_IF_NAME).ipv6.address
        assert (
            ipaddress.ip_address(actual_address) ==
            ipaddress.ip_address(ip_address)
        )


def set_postcopy_migration_policy(system_service):
    cluster_service = test_utils.get_cluster_service(system_service, CLUSTER_NAME)
    cluster_service.update(
        cluster=Cluster(
            migration=MigrationOptions(
                policy=MigrationPolicy(
                    id=MIGRATION_POLICY_POSTCOPY
                )
            )
        )
    )


def test_ipv4_migration(all_hosts_hostnames, ansible_by_hostname, system_service,
                        prepare_migration_vlan):
    prepare_migration_attachments_ipv4(system_service)
    migrate_vm(all_hosts_hostnames, ansible_by_hostname, system_service)


def test_ipv6_migration(all_hosts_hostnames, ansible_by_hostname, system_service,
                        prepare_migration_vlan):
    prepare_migration_attachments_ipv6(system_service)
    set_postcopy_migration_policy(system_service)
    migrate_vm(all_hosts_hostnames, ansible_by_hostname, system_service)
