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


# DC/Cluster
DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

# Network
MANAGEMENT_NET = 'ovirtmgmt'

VLAN100_NET = 'VLAN100_Network'
VLAN100_NET_IPv4_ADDR = '192.0.2.1'
VLAN100_NET_IPv4_MASK = '255.255.255.0'
VLAN100_NET_IPv6_ADDR = '2001:0db8:85a3:0000:0000:8a2e:0370:7331'
VLAN100_NET_IPv6_MASK = '64'


def _hosts_in_cluster(api, cluster_name):
    hosts = api.hosts.list(query='cluster={}'.format(cluster_name))
    return sorted(hosts, key=lambda host: host.name)


def _get_networkattachment_by_network_id(host, network_id):
    # ovirtsdk requires '.' as a separator in multi-level filtering, we cannot
    # use kwargs directly
    # caveat: filtering by network.name is not supported by design (RH 1382341)
    # as only 'id' and 'href' properties are resolved for nested objects
    filter_args = {'network.id': network_id}
    attachment = host.networkattachments.list(**filter_args)[0]
    return attachment


def _set_network_required_in_cluster(api, network_name, cluster_name,
                                     required):
    network = api.clusters.get(cluster_name).networks.get(name=network_name)
    network.set_required(required)
    network.update()


def _get_mgmt_attachment(api, host):
    dc = api.datacenters.get(name=DC_NAME)
    mgmt_network_id = dc.networks.get(name=MANAGEMENT_NET).id
    mgmt_attachment = _get_networkattachment_by_network_id(
        host, mgmt_network_id)
    return mgmt_attachment


def _create_ip_configuration():
    ip_configuration = params.IpAddressAssignments(ip_address_assignment=[
        params.IpAddressAssignment(
            assignment_method='static',
            ip=params.IP(
                address=VLAN100_NET_IPv4_ADDR,
                netmask=VLAN100_NET_IPv4_MASK)),
        params.IpAddressAssignment(
            assignment_method='static',
            ip=params.IP(
                address=VLAN100_NET_IPv6_ADDR,
                netmask=VLAN100_NET_IPv6_MASK,
                version='v6'))
    ])

    return ip_configuration


def _attach_vlan_to_host(api, host, ip_configuration):
    mgmt_attachment = _get_mgmt_attachment(api, host)
    mgmt_nic_id = mgmt_attachment.get_host_nic().id
    mgmt_nic_name = host.nics.get(id=mgmt_nic_id).name

    vlan_network_attachment = params.NetworkAttachment(
        network=params.Network(name=VLAN100_NET),
        host_nic=params.HostNIC(name=mgmt_nic_name),
        ip_address_assignments=ip_configuration)

    attachment_action = params.Action(
        modified_network_attachments=params.NetworkAttachments(
            network_attachment=[vlan_network_attachment]),
        check_connectivity=True)

    host.setupnetworks(attachment_action)


#


@testlib.with_ovirt_api
def attach_vlan_to_host(api):
    host = _hosts_in_cluster(api, CLUSTER_NAME)[0]
    ip_configuration = _create_ip_configuration()
    _attach_vlan_to_host(api, host, ip_configuration)

    # TODO: currently ost uses v3 SDK that doesn't report ipv6. once available,
    # verify ipv6 as well.
    nt.assert_equals(
        host.nics.list(name='eth0.100')[0].ip.address,
        VLAN100_NET_IPv4_ADDR)


@testlib.with_ovirt_api
def detach_vlan_from_host(api):
    network_id = api.networks.get(name=VLAN100_NET).id
    host = _hosts_in_cluster(api, CLUSTER_NAME)[0]

    def _detach_vlan_from_host():
        attachment = _get_networkattachment_by_network_id(host, network_id)

        removal_action = params.Action(
            removed_network_attachments=params.NetworkAttachments(
                network_attachment=[params.NetworkAttachment(
                    id=attachment.id)]))

        host.setupnetworks(removal_action)

    def _host_is_detached_from_vlan_network():
        with nt.assert_raises(IndexError):
            _get_networkattachment_by_network_id(host, network_id)
        return True

    _set_network_required_in_cluster(api, VLAN100_NET, CLUSTER_NAME, False)
    _detach_vlan_from_host()

    nt.assert_true(_host_is_detached_from_vlan_network())


_TEST_LIST = [
    attach_vlan_to_host,
    detach_vlan_from_host
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
