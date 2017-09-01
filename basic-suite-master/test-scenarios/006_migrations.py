#
# Copyright 2016-2017 Red Hat, Inc.
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

from netaddr.ip import IPAddress
import nose.tools as nt
from ovirtlago import testlib
from ovirtsdk4.types import Host, NetworkUsage, VmStatus

import test_utils
from test_utils import network_utils_v4


DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

NIC_NAME = 'eth0'
VLAN200_IF_NAME = '{}.200'.format(NIC_NAME)

DEFAULT_MTU = 1500

MIGRATION_NETWORK = 'Migration_Net'
MIGRATION_NETWORK_IPv4_ADDR = '192.0.3.{}'
MIGRATION_NETWORK_IPv4_MASK = '255.255.255.0'
MIGRATION_NETWORK_IPv6_ADDR = '1001:0db8:85a3:0000:0000:574c:14ea:0a0{}'
MIGRATION_NETWORK_IPv6_MASK = '64'

VM0_NAME = 'vm0'


@testlib.with_ovirt_api4
def prepare_migration_vlan(api):
    engine = api.system_service()

    nt.assert_true(
        network_utils_v4.set_network_usages_in_cluster(
            engine, MIGRATION_NETWORK, CLUSTER_NAME, [NetworkUsage.MIGRATION])
    )

    # Set Migration_Network's MTU to match the other VLAN's on the NIC.
    nt.assert_true(
        network_utils_v4.set_network_mtu(
            engine, MIGRATION_NETWORK, DC_NAME, DEFAULT_MTU)
    )


@testlib.with_ovirt_api4
@testlib.with_ovirt_prefix
def migrate_vm(prefix, api):
    engine = api.system_service()

    def current_running_host():
        vm = engine.vms_service().list(search='name={}'.format(VM0_NAME))[0]
        host = engine.hosts_service().list(
            search='id={}'.format(vm.host.id))[0]
        return host.name

    src_host = current_running_host()
    dst_host = sorted([h.name() for h in prefix.virt_env.host_vms()
                       if h.name() != src_host])[0]

    vm = engine.vms_service().list(search='name={}'.format(VM0_NAME))[0]
    # migrate() currently only returns None, but checks for errors internally
    engine.vms_service().vm_service(vm.id).migrate(host=Host(name=dst_host))

    testlib.assert_true_within_short(
        lambda: engine.vms_service().list(
            search='name={}'.format(VM0_NAME))[0].status == VmStatus.UP
    )

    nt.assert_equals(
        current_running_host(), dst_host
    )


@testlib.with_ovirt_api4
def prepare_migration_attachments_ipv4(api):
    engine = api.system_service()

    for index, host in enumerate(
            test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME),
            start=1):
        host_service = engine.hosts_service().host_service(id=host.id)

        ip_address = MIGRATION_NETWORK_IPv4_ADDR.format(index)

        ip_configuration = network_utils_v4.create_static_ip_configuration(
            ipv4_addr=ip_address,
            ipv4_mask=MIGRATION_NETWORK_IPv4_MASK)

        network_utils_v4.attach_network_to_host(
            host_service, NIC_NAME, MIGRATION_NETWORK, ip_configuration)

        actual_address = next(nic for nic in host_service.nics_service().list()
                              if nic.name == VLAN200_IF_NAME).ip.address
        nt.assert_equals(IPAddress(actual_address), IPAddress(ip_address))


@testlib.with_ovirt_api4
def prepare_migration_attachments_ipv6(api):
    engine = api.system_service()

    for index, host in enumerate(
            test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME),
            start=1):
        host_service = engine.hosts_service().host_service(id=host.id)

        ip_address = MIGRATION_NETWORK_IPv6_ADDR.format(index)

        ip_configuration = network_utils_v4.create_static_ip_configuration(
            ipv6_addr=ip_address,
            ipv6_mask=MIGRATION_NETWORK_IPv6_MASK)

        network_utils_v4.modify_ip_config(
            engine, host_service, MIGRATION_NETWORK, ip_configuration)

        actual_address = next(nic for nic in host_service.nics_service().list()
                              if nic.name == VLAN200_IF_NAME).ipv6.address
        nt.assert_equals(IPAddress(actual_address), IPAddress(ip_address))


_TEST_LIST = [
    prepare_migration_vlan,

    prepare_migration_attachments_ipv4,
    migrate_vm,

    # NOTE: IPv6 migration now trivially works, as ip6tables replace firewalld
    #       and leave ports open. See https://bugzilla.redhat.com/1414524
    prepare_migration_attachments_ipv6,
    migrate_vm,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
