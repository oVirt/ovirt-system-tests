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

from ovirtsdk.xml import params


def attach_network_to_host(api, host, nic_name, network_name,
                           ip_configuration, bonds=[]):
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


def create_static_ip_configuration(ipv4_addr=None, ipv4_mask=None,
                                   ipv6_addr=None, ipv6_mask=None):
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

    return params.IpAddressAssignments(
        ip_address_assignment=assignments)


def create_network_params(network_name, dc_name, **net_params):
    return params.Network(
        name=network_name,
        data_center=params.DataCenter(
            name=dc_name,
        ),
        **net_params
    )
