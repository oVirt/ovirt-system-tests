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


def set_network_usages_in_cluster(api, network_name, cluster_name, usages):
    cluster = api.clusters.get(cluster_name)
    cluster_network = cluster.networks.get(network_name)
    cluster_network.set_usages(usages)
    return cluster_network.update()


def set_network_mtu(api, network_name, dc_name, mtu):
    dc = api.datacenters.get(dc_name)
    network = dc.networks.get(network_name)
    network.set_mtu(mtu)
    return network.update()


def create_network_params(network_name, dc_name, **net_params):
    return params.Network(
        name=network_name,
        data_center=params.DataCenter(
            name=dc_name,
        ),
        **net_params
    )
