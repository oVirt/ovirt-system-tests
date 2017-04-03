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

import test_utils
from test_utils import network_utils_v3


# DC/Cluster
DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

# Network
VM_NETWORK = 'VM_Network'
VM_NETWORK_IPv4_ADDR = '192.0.2.1'
VM_NETWORK_IPv4_MASK = '255.255.255.0'
VM_NETWORK_IPv6_ADDR = '2001:0db8:85a3:0000:0000:8a2e:0370:7331'
VM_NETWORK_IPv6_MASK = '64'
NIC_NAME = 'eth0'
VM_NETWORK_VLAN_ID = 100
VLAN_IF_NAME = '{}.{}'.format(NIC_NAME, VM_NETWORK_VLAN_ID)


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


_TEST_LIST = [
    attach_vm_network_to_host_static_config,
    modify_host_ip_to_dhcp,
    # TODO: move to 0xx_networks_teardown so we can actually use the network
    detach_vm_network_from_host,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
