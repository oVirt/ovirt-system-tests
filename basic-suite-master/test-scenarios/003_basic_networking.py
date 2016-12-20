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

from test_utils import network_utils


# DC/Cluster
DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

# Network
MANAGEMENT_NET = 'ovirtmgmt'
NIC_NAME = 'eth0'
VLAN_IF_NAME = '%s.100' % (NIC_NAME,)

VLAN100_NET = 'VLAN100_Network'
VLAN100_NET_IPv4_ADDR = '192.0.2.1'
VLAN100_NET_IPv4_MASK = '255.255.255.0'
VLAN100_NET_IPv6_ADDR = '2001:0db8:85a3:0000:0000:8a2e:0370:7331'
VLAN100_NET_IPv6_MASK = '64'


def _hosts_in_cluster(api, cluster_name):
    hosts = api.hosts.list(query='cluster={}'.format(cluster_name))
    return sorted(hosts, key=lambda host: host.name)


@testlib.with_ovirt_api
def attach_vlan_to_host_static_config(api):
    host = _hosts_in_cluster(api, CLUSTER_NAME)[0]
    ip_configuration = network_utils.create_static_ip_configuration(
        VLAN100_NET_IPv4_ADDR,
        VLAN100_NET_IPv4_MASK,
        VLAN100_NET_IPv6_ADDR,
        VLAN100_NET_IPv6_MASK)

    network_utils.attach_vlan_to_host(
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
    network_id = api.networks.get(name=VLAN100_NET).id
    host = _hosts_in_cluster(api, CLUSTER_NAME)[0]

    def _host_is_detached_from_vlan_network():
        with nt.assert_raises(IndexError):
            attachment = network_utils.get_network_attachment(
                api, host, VLAN100_NET, DC_NAME)
        return True

    network_utils.set_network_required_in_cluster(
        api, VLAN100_NET, CLUSTER_NAME, False)
    network_utils.detach_vlan_from_host(api, host, NIC_NAME, VLAN100_NET)

    nt.assert_true(_host_is_detached_from_vlan_network())


_TEST_LIST = [
    attach_vlan_to_host_static_config,
    modify_host_ip_to_dhcp,
    detach_vlan_from_host
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
