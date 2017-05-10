#
# Copyright 2017 Red Hat, Inc.
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

from ovirtsdk4.types import (BootProtocol, HostNic, Ip, IpAddressAssignment,
                             IpVersion, Network, NetworkAttachment)

import test_utils


def _get_attachment_by_id(host, network_id):
    return next(att for att in host.network_attachments_service().list()
                if att.network.id == network_id)


def attach_network_to_host(host, nic_name, network_name, ip_configuration,
                           bonds=[]):
    attachment = NetworkAttachment(
        network=Network(name=network_name),
        host_nic=HostNic(name=nic_name),
        ip_address_assignments=ip_configuration)

    return host.setup_networks(
        modified_bonds=bonds,
        modified_network_attachments=[attachment],
        check_connectivity=True)


def detach_network_from_host(engine, host, network_name, bond_name=None):
    network_id = engine.networks_service().list(
        search='name={}'.format(network_name))[0].id

    attachment = _get_attachment_by_id(host, network_id)
    bonds = [nic for nic in host.nics_service().list() if bond_name and
             nic.name == bond_name]  # there is no more than one bond

    return host.setup_networks(
        removed_bonds=bonds,
        removed_network_attachments=[attachment],
        check_connectivity=True)


def modify_ip_config(engine, host, network_name, ip_configuration):
    network_id = engine.networks_service().list(
        search='name={}'.format(network_name))[0].id

    attachment = _get_attachment_by_id(host, network_id)
    attachment.ip_address_assignments = ip_configuration

    return host.setup_networks(modified_network_attachments=[attachment],
                               check_connectivity=True)


def create_dhcp_ip_configuration():
    return [
        IpAddressAssignment(assignment_method=BootProtocol.DHCP),
        IpAddressAssignment(assignment_method=BootProtocol.DHCP,
                            ip=Ip(version=IpVersion.V6))
    ]


def create_static_ip_configuration(ipv4_addr=None, ipv4_mask=None,
                                   ipv6_addr=None, ipv6_mask=None):
    assignments = []
    if ipv4_addr:
        assignments.append(IpAddressAssignment(
            assignment_method=BootProtocol.STATIC,
            ip=Ip(
                address=ipv4_addr,
                netmask=ipv4_mask)))
    if ipv6_addr:
        assignments.append(IpAddressAssignment(
            assignment_method=BootProtocol.STATIC,
            ip=Ip(
                address=ipv6_addr,
                netmask=ipv6_mask,
                version=IpVersion.V6)))

    return assignments


def get_network_attachment(engine, host, network_name, dc_name):
    dc = test_utils.data_center_service(engine, dc_name)

    # CAVEAT: .list(search='name=Migration_Network') is ignored, and the first
    #         network returned happened to be VM_Network in my case
    network = next(net for net in dc.networks_service().list()
                   if net.name == network_name)

    return _get_attachment_by_id(host, network.id)


def set_network_usages_in_cluster(engine, network_name, cluster_name, usages):
    clusters_service = engine.clusters_service()
    cluster = clusters_service.list(search='name={}'.format(cluster_name))[0]
    cluster_service = clusters_service.cluster_service(cluster.id)

    network = engine.networks_service().list(
        search='name={}'.format(network_name))[0]
    network_service = cluster_service.networks_service().network_service(
        id=network.id)

    network.usages = usages

    return network_service.update(network)


def set_network_required_in_cluster(engine, network_name, cluster_name,
                                    required):
    clusters_service = engine.clusters_service()
    cluster = clusters_service.list(search='name={}'.format(cluster_name))[0]
    cluster_service = clusters_service.cluster_service(cluster.id)

    network = engine.networks_service().list(
        search='name={}'.format(network_name))[0]
    network_service = cluster_service.networks_service().network_service(
        id=network.id)

    network.required = required

    return network_service.update(network)


def set_network_mtu(engine, network_name, dc_name, mtu):
    dc = test_utils.data_center_service(engine, dc_name)

    network = next(net for net in dc.networks_service().list()
                   if net.name == network_name)
    network_service = dc.networks_service().network_service(id=network.id)

    network.mtu = mtu

    return network_service.update(network)
