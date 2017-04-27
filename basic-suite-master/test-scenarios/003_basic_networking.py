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

from lago import utils
from netaddr.ip import IPAddress
import nose.tools as nt
from ovirtlago import testlib
from ovirtsdk.xml import params

import test_utils
from test_utils import network_utils_v3, network_utils_v4


# Environment (see control.sh and LagoInitFile.in)
LIBVIRT_NETWORK_FOR_MANAGEMENT = testlib.get_prefixed_name('net-management')  # eth0
LIBVIRT_NETWORK_FOR_BONDING = testlib.get_prefixed_name('net-bonding')  # eth2, eth3

# DC/Cluster
DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

# Networks
VM_NETWORK = 'VM_Network'
VM_NETWORK_IPv4_ADDR = '192.0.2.1'
VM_NETWORK_IPv4_MASK = '255.255.255.0'
VM_NETWORK_IPv6_ADDR = '2001:0db8:85a3:0000:0000:8a2e:0370:7331'
VM_NETWORK_IPv6_MASK = '64'
VM_NETWORK_VLAN_ID = 100

MIGRATION_NETWORK = 'Migration_Net'  # MTU 9000
BOND_NAME = 'bond0'
MIGRATION_NETWORK_IPv4_ADDR = '192.0.3.{}'
MIGRATION_NETWORK_IPv4_MASK = '255.255.255.0'
MIGRATION_NETWORK_IPv6_ADDR = '2001:0db8:85a3:0000:0000:574c:14ea:0a0{}'
MIGRATION_NETWORK_IPv6_MASK = '64'


def _host_vm_nics(prefix, host_name, network_name):
    """
    Return names of host VM NICs attached by Lago to a given libvirt network,
    just like do_status in site-packages/lago/cmd.py:446

    TODO: move 'eth{0}' magic to site-packages/ovirtlago/testlib.py?
    """
    lago_host_vm = prefix.get_vms()[host_name]
    return ['eth{0}'.format(i) for i, nic in enumerate(lago_host_vm.nics())
            if nic['net'] == network_name]


def _ping(host, ip_address):
    """
    Ping a given address (IPv4/6) from a host.
    """
    cmd = ['ping', '-c', '1']
    # TODO: support pinging by host names?
    if ':' in ip_address:
        cmd += ['-6']

    ret = host.ssh(cmd + [ip_address])
    nt.assert_equals(ret.code, 0, 'Cannot ping {} from {}: {}'.format(
        ip_address, host.name(), ret))


def _host_is_attached_to_network(api, host, network_name, nic_name=None):
    try:
        attachment = network_utils_v3.get_network_attachment(
            api, host, network_name, DC_NAME)
    except IndexError:  # there is no attachment of the network to the host
        return False

    if nic_name:
        host_nic = host.nics.get(id=attachment.host_nic.id)
        nt.assert_equals(nic_name, host_nic.name)
    return attachment


@testlib.with_ovirt_api4
@testlib.with_ovirt_prefix
def attach_vm_network_to_host_static_config(prefix, api):
    engine = api.system_service()

    host = test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME)[0]
    host_service = engine.hosts_service().host_service(id=host.id)

    nic_name = _host_vm_nics(prefix, host.name,
                             LIBVIRT_NETWORK_FOR_MANAGEMENT)[0]  # eth0
    ip_configuration = network_utils_v4.create_static_ip_configuration(
        VM_NETWORK_IPv4_ADDR,
        VM_NETWORK_IPv4_MASK,
        VM_NETWORK_IPv6_ADDR,
        VM_NETWORK_IPv6_MASK)

    network_utils_v4.attach_network_to_host(
        host_service,
        nic_name,
        VM_NETWORK,
        ip_configuration)

    host_nic = next(nic for nic in host_service.nics_service().list() if
                    nic.name == '{}.{}'.format(nic_name, VM_NETWORK_VLAN_ID))
    nt.assert_equals(IPAddress(host_nic.ip.address),
                     IPAddress(VM_NETWORK_IPv4_ADDR))
    nt.assert_equals(IPAddress(host_nic.ipv6.address),
                     IPAddress(VM_NETWORK_IPv6_ADDR))


@testlib.with_ovirt_api4
def modify_host_ip_to_dhcp(api):
    engine = api.system_service()

    host = test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME)[0]
    host_service = engine.hosts_service().host_service(id=host.id)
    ip_configuration = network_utils_v4.create_dhcp_ip_configuration()

    network_utils_v4.modify_ip_config(engine, host_service, VM_NETWORK,
                                      ip_configuration)

    # TODO: once the VLANs/dnsmasq issue is resolved,
    # (https://github.com/lago-project/lago/issues/375)
    # verify ip configuration.


@testlib.with_ovirt_api
def detach_vm_network_from_host(api):
    host = test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME)[0]

    network_utils_v3.set_network_required_in_cluster(
        api, VM_NETWORK, CLUSTER_NAME, False)
    network_utils_v3.detach_network_from_host(api, host, VM_NETWORK)

    nt.assert_false(_host_is_attached_to_network(api, host, VM_NETWORK))


@testlib.with_ovirt_api
@testlib.with_ovirt_prefix
def bond_nics(prefix, api):
    def _bond_nics(number, host):
        slaves = params.Slaves(host_nic=[
            params.HostNIC(name=nic) for nic in _host_vm_nics(
                prefix, host.name, LIBVIRT_NETWORK_FOR_BONDING)])  # eth2, eth3

        options = params.Options(option=[
            params.Option(name='mode', value='active-backup'),
            params.Option(name='miimon', value='200'),
            ])

        bond = params.HostNIC(
            name=BOND_NAME,
            bonding=params.Bonding(slaves=slaves, options=options))

        ip_configuration = network_utils_v3.create_static_ip_configuration(
            MIGRATION_NETWORK_IPv4_ADDR.format(number),
            MIGRATION_NETWORK_IPv4_MASK,
            MIGRATION_NETWORK_IPv6_ADDR.format(number),
            MIGRATION_NETWORK_IPv6_MASK)

        network_utils_v3.attach_network_to_host(
            api, host, BOND_NAME, MIGRATION_NETWORK, ip_configuration, [bond])

    hosts = test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME)
    utils.invoke_in_parallel(_bond_nics, range(1, len(hosts) + 1), hosts)

    for host in test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME):
        nt.assert_true(_host_is_attached_to_network(
            api, host, MIGRATION_NETWORK, nic_name=BOND_NAME))


@testlib.with_ovirt_prefix
def verify_interhost_connectivity_ipv4(prefix):
    first_host = prefix.virt_env.host_vms()[0]
    _ping(first_host, MIGRATION_NETWORK_IPv4_ADDR.format(2))


@testlib.with_ovirt_prefix
def verify_interhost_connectivity_ipv6(prefix):
    first_host = prefix.virt_env.host_vms()[0]
    _ping(first_host, MIGRATION_NETWORK_IPv6_ADDR.format(2))


@testlib.with_ovirt_api
def remove_bonding(api):
    def _remove_bonding(host):
        network_utils_v3.detach_network_from_host(api, host, MIGRATION_NETWORK,
                                                  BOND_NAME)

    network_utils_v3.set_network_required_in_cluster(api, MIGRATION_NETWORK,
                                                     CLUSTER_NAME, False)
    utils.invoke_in_parallel(_remove_bonding,
                             test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME))

    for host in test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME):
        nt.assert_false(_host_is_attached_to_network(api, host,
                                                     MIGRATION_NETWORK))


_TEST_LIST = [
    attach_vm_network_to_host_static_config,
    modify_host_ip_to_dhcp,
    detach_vm_network_from_host,
    bond_nics,
    verify_interhost_connectivity_ipv4,
    verify_interhost_connectivity_ipv6,
    remove_bonding,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
