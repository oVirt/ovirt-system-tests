#
# Copyright 2016 Red Hat, Inc.
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
import nose.tools as nt
from ovirtsdk.xml import params

from lago import utils
from ovirtlago import testlib

import test_utils
from test_utils import network_utils_v3


# Environment (see control.sh and LagoInitFile.in)
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
NIC_NAME = 'eth0'
VM_NETWORK_VLAN_ID = 100
VLAN_IF_NAME = '{}.{}'.format(NIC_NAME, VM_NETWORK_VLAN_ID)

MIGRATION_NETWORK = 'VLAN200_Network'
BOND_NAME = 'bond0'
MIGRATION_NETWORK_IPv4_ADDR = '192.0.3.%d'
MIGRATION_NETWORK_IPv4_MASK = '255.255.255.0'
MIGRATION_NETWORK_IPv6_ADDR = '2001:0db8:85a3:0000:0000:574c:14ea:0a0%d'
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


@testlib.with_ovirt_api
def attach_vm_network_to_host_static_config(api):
    host = test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME)[0]
    ip_configuration = network_utils_v3.create_static_ip_configuration(
        VM_NETWORK_IPv4_ADDR,
        VM_NETWORK_IPv4_MASK,
        VM_NETWORK_IPv6_ADDR,
        VM_NETWORK_IPv6_MASK)

    network_utils_v3.attach_network_to_host(
        api,
        host,
        NIC_NAME,
        VM_NETWORK,
        ip_configuration)

    # TODO: currently ost uses v3 SDK that doesn't report ipv6. once available,
    # verify ipv6 as well.
    nt.assert_equals(
        host.nics.list(name=VLAN_IF_NAME)[0].ip.address,
        VM_NETWORK_IPv4_ADDR)


@testlib.with_ovirt_api
def modify_host_ip_to_dhcp(api):
    host = test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME)[0]
    ip_configuration = network_utils_v3.create_dhcp_ip_configuration()
    network_utils_v3.modify_ip_config(api, host, VM_NETWORK, ip_configuration)

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
            MIGRATION_NETWORK_IPv4_ADDR % number, MIGRATION_NETWORK_IPv4_MASK,
            MIGRATION_NETWORK_IPv6_ADDR % number, MIGRATION_NETWORK_IPv6_MASK)

        network_utils_v3.attach_network_to_host(
            api, host, BOND_NAME, MIGRATION_NETWORK, ip_configuration, [bond])

    hosts = test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME)
    utils.invoke_in_parallel(_bond_nics, range(1, len(hosts) + 1), hosts)

    for host in test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME):
        nt.assert_true(_host_is_attached_to_network(
            api, host, MIGRATION_NETWORK, nic_name=BOND_NAME))


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
    # TODO: move to 0xx_networks_teardown so we can actually use the network
    detach_vm_network_from_host,
    bond_nics,
    remove_bonding,  # TODO: move to 0xx_networks_teardown as well
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
