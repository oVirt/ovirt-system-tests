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

from ovirtlago import testlib
from lago import utils

from test_utils import network_utils


# Environment (see control.sh and LagoInitFile.in)
LIBVIRT_NETWORK_FOR_BONDING = testlib.get_prefixed_name('net-bonding')

# DC/Cluster
DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

# Networks
NIC_NAME = 'eth0'
VLAN_IF_NAME = '%s.100' % (NIC_NAME,)

VLAN100_NET = 'VLAN100_Network'
VLAN100_NET_IPv4_ADDR = '192.0.2.1'
VLAN100_NET_IPv4_MASK = '255.255.255.0'
VLAN100_NET_IPv6_ADDR = '2001:0db8:85a3:0000:0000:8a2e:0370:7331'
VLAN100_NET_IPv6_MASK = '64'

VLAN200_NET = 'VLAN200_Network'  # MTU 9000
BOND_NAME = 'bond0'
VLAN200_NET_IPv4_ADDR = '192.0.3.%d'
VLAN200_NET_IPv4_MASK = '255.255.255.0'
VLAN200_NET_IPv6_ADDR = '2001:0db8:85a3:0000:0000:574c:14ea:0a0%d'
VLAN200_NET_IPv6_MASK = '64'


def _nics_to_bond(prefix, host_name):
    """
    Return names of NICs (from a Lago host VM) to be bonded,
    just like do_status in site-packages/lago/cmd.py:446

    TODO: move 'eth{0}' magic to site-packages/ovirtlago/testlib.py?
    """
    lago_host_vm = prefix.get_vms()[host_name]
    return ['eth{0}'.format(i) for i, nic in enumerate(lago_host_vm.nics())
            if nic['net'] == LIBVIRT_NETWORK_FOR_BONDING]


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


def _hosts_in_cluster(api, cluster_name):
    hosts = api.hosts.list(query='cluster={}'.format(cluster_name))
    return sorted(hosts, key=lambda host: host.name)


def _host_is_attached_to_network(api, host, network_name, nic_name=None):
    try:
        attachment = network_utils.get_network_attachment(
            api, host, network_name, DC_NAME)
    except IndexError:  # there is no attachment of the network to the host
        return False

    if nic_name:
        host_nic = host.nics.get(id=attachment.host_nic.id)
        nt.assert_equals(nic_name, host_nic.name)
    return attachment


@testlib.with_ovirt_api
def attach_vlan_to_host_static_config(api):
    host = _hosts_in_cluster(api, CLUSTER_NAME)[0]
    ip_configuration = network_utils.create_static_ip_configuration(
        VLAN100_NET_IPv4_ADDR,
        VLAN100_NET_IPv4_MASK,
        VLAN100_NET_IPv6_ADDR,
        VLAN100_NET_IPv6_MASK)

    network_utils.attach_network_to_host(
        api,
        host,
        NIC_NAME,
        VLAN100_NET,
        ip_configuration)

    # TODO: currently ost uses v3 SDK that doesn't report ipv6. once available,
    # verify ipv6 as well.
    nt.assert_equals(
        host.nics.list(name=VLAN_IF_NAME)[0].ip.address,
        VLAN100_NET_IPv4_ADDR)


@testlib.with_ovirt_api
def modify_host_ip_to_dhcp(api):
    host = _hosts_in_cluster(api, CLUSTER_NAME)[0]
    ip_configuration = network_utils.create_dhcp_ip_configuration()
    network_utils.modify_ip_config(api, host, VLAN100_NET, ip_configuration)

    # TODO: once the VLANs/dnsmasq issue is resolved,
    # (https://github.com/lago-project/lago/issues/375)
    # verify ip configuration.


@testlib.with_ovirt_api
def detach_vlan_from_host(api):
    host = _hosts_in_cluster(api, CLUSTER_NAME)[0]

    network_utils.set_network_required_in_cluster(
        api, VLAN100_NET, CLUSTER_NAME, False)
    network_utils.detach_network_from_host(api, host, VLAN100_NET)

    nt.assert_false(_host_is_attached_to_network(api, host, VLAN100_NET))


@testlib.with_ovirt_api
@testlib.with_ovirt_prefix
def bond_nics(prefix, api):
    def _bond_nics(number, host):
        slaves = params.Slaves(host_nic=[
            params.HostNIC(name=nic) for nic in _nics_to_bond(
                prefix, host.name)])

        options = params.Options(option=[
            params.Option(name='mode', value='active-backup'),
            params.Option(name='miimon', value='200'),
            ])

        bond = params.HostNIC(
            name=BOND_NAME,
            bonding=params.Bonding(slaves=slaves, options=options))

        ip_configuration = network_utils.create_static_ip_configuration(
            VLAN200_NET_IPv4_ADDR % number, VLAN200_NET_IPv4_MASK,
            VLAN200_NET_IPv6_ADDR % number, VLAN200_NET_IPv6_MASK)

        network_utils.attach_network_to_host(
            api, host, BOND_NAME, VLAN200_NET, ip_configuration, [bond])

    hosts = _hosts_in_cluster(api, CLUSTER_NAME)
    utils.invoke_in_parallel(_bond_nics, range(1, len(hosts) + 1), hosts)

    for host in _hosts_in_cluster(api, CLUSTER_NAME):
        nt.assert_true(_host_is_attached_to_network(api, host, VLAN200_NET,
                                                    nic_name=BOND_NAME))


@testlib.with_ovirt_prefix
def verify_interhost_connectivity_ipv4(prefix):
    first_host = prefix.virt_env.host_vms()[0]
    _ping(first_host, VLAN200_NET_IPv4_ADDR % 2)


@testlib.with_ovirt_prefix
def verify_interhost_connectivity_ipv6(prefix):
    first_host = prefix.virt_env.host_vms()[0]
    _ping(first_host, VLAN200_NET_IPv6_ADDR % 2)


@testlib.with_ovirt_api
def remove_bonding(api):
    def _remove_bonding(host):
        network_utils.detach_network_from_host(api, host, VLAN200_NET,
                                               BOND_NAME)

    network_utils.set_network_required_in_cluster(api, VLAN200_NET,
                                                  CLUSTER_NAME, False)
    utils.invoke_in_parallel(_remove_bonding,
                             _hosts_in_cluster(api, CLUSTER_NAME))

    for host in _hosts_in_cluster(api, CLUSTER_NAME):
        nt.assert_false(_host_is_attached_to_network(api, host, VLAN200_NET))


_TEST_LIST = [
    attach_vlan_to_host_static_config,
    modify_host_ip_to_dhcp,
    detach_vlan_from_host,
    bond_nics,
    verify_interhost_connectivity_ipv4,
    verify_interhost_connectivity_ipv6,
    remove_bonding,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
