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
from ovirtsdk.xml import params


def _get_attachment_by_id(host, network_id):
    # ovirtsdk requires '.' as a separator in multi-level filtering, we cannot
    # use kwargs directly
    # caveat: filtering by network.name is not supported by design (RH 1382341)
    # as only 'id' and 'href' properties are resolved for nested objects
    filter_args = {'network.id': network_id}
    attachment = host.networkattachments.list(**filter_args)[0]
    return attachment


def attach_network_to_host(api,
                           host,
                           nic_name,
                           network_name,
                           ip_configuration,
                           bonds=[]):
    network_attachment = params.NetworkAttachment(
        network=params.Network(name=network_name),
        host_nic=params.HostNIC(name=nic_name),
        ip_address_assignments=ip_configuration)

    attachment_action = params.Action(
        modified_bonds=params.HostNics(host_nic=bonds),
        modified_network_attachments=params.NetworkAttachments(
            network_attachment=[network_attachment]),
        check_connectivity=True)

    return host.setupnetworks(attachment_action)


def detach_network_from_host(api,
                             host,
                             network_name,
                             bond_name=None):
    network_id = api.networks.get(name=network_name).id
    attachment = _get_attachment_by_id(host, network_id)
    bonds = [nic for nic in host.nics.list() if bond_name and
             nic.name == bond_name]  # there is no more than one bond

    removal_action = params.Action(
        removed_bonds=params.HostNics(host_nic=bonds),
        removed_network_attachments=params.NetworkAttachments(
            network_attachment=[params.NetworkAttachment(
                id=attachment.id)]))

    return host.setupnetworks(removal_action)


def modify_ip_config(api,
                     host,
                     network_name,
                     ip_configuration):
    network_id = api.networks.get(name=network_name).id
    attachment = _get_attachment_by_id(host, network_id)
    attachment.set_ip_address_assignments(ip_configuration)

    attachment_action = params.Action(
        modified_network_attachments=params.NetworkAttachments(
            network_attachment=[attachment]),
        check_connectivity=True)

    return host.setupnetworks(attachment_action)


def create_dhcp_ip_configuration():
    ip_configuration=params.IpAddressAssignments(ip_address_assignment = [
        params.IpAddressAssignment(
            assignment_method='dhcp'),
        params.IpAddressAssignment(
            assignment_method='dhcp',
            ip=params.IP(version='v6'))
    ])

    return ip_configuration


def create_static_ip_configuration(ipv4_addr = None,
                                    ipv4_mask = None,
                                    ipv6_addr = None,
                                    ipv6_mask = None):
    assignments = []
    if ipv4_addr:
        assignments.append(params.IpAddressAssignment(
            assignment_method='static',
            ip=params.IP(
                address=ipv4_addr,
                netmask=ipv4_mask)))
    if ipv6_addr:
        assignments.append(params.IpAddressAssignment(
            assignment_method='static',
            ip=params.IP(
                address=ipv6_addr,
                netmask=ipv6_mask,
                version='v6')))

    ip_configuration=params.IpAddressAssignments(
        ip_address_assignment=assignments)
    return ip_configuration


def get_management_attachment(api,
                              host,
                              dc_name):
    return get_network_attachment(api, host, 'ovirtmgmt', dc_name)


def get_network_attachment(api,
                           host,
                           net_name,
                           dc_name):
    dc = api.datacenters.get(name=dc_name)
    network_id = dc.networks.get(name=net_name).id
    attachment = _get_attachment_by_id(host, network_id)
    return attachment


def set_network_usages_in_cluster(api,
                                  network_name,
                                  cluster_name,
                                  usages):
    cluster = api.clusters.get(cluster_name)
    cluster_network = cluster.networks.get(network_name)
    cluster_network.set_usages(usages)
    return cluster_network.update()


def get_network_usages_in_cluster(api,
                                  network_name,
                                  cluster_name):
    cluster = api.clusters.get(cluster_name)
    cluster_network = cluster.networks.get(network_name)
    return cluster_network.get_usages().usage


def set_network_required_in_cluster(api,
                                    network_name,
                                    cluster_name,
                                    required):
    cluster = api.clusters.get(cluster_name)
    cluster_network = cluster.networks.get(network_name)
    cluster_network.set_required(required)
    return cluster_network.update()


def set_network_mtu(api,
                    network_name,
                    dc_name,
                    mtu):
    dc = api.datacenters.get(dc_name)
    network = dc.networks.get(network_name)
    network.set_mtu(mtu)
    return network.update()


def create_network_params(network_name,
                          dc_name,
                          **net_params):
     return params.Network(
        name=network_name,
        data_center=params.DataCenter(
            name=dc_name,
        ),
        **net_params
    )
