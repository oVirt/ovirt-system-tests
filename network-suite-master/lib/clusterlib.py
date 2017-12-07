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
from ovirtsdk4 import types

from lib.sdkentity import SDKEntity


class Cluster(SDKEntity):

    @property
    def name(self):
        return self.sdk_type.name

    def networks(self):
        networks = []
        for sdk_net in self._service.networks_service().list():
            cluster_network = ClusterNetwork(self)
            cluster_network.import_by_id(sdk_net.id)
            networks.append(cluster_network)
        return networks

    def mgmt_network(self):
        return next(network for network in self.networks() if
                    types.NetworkUsage.MANAGEMENT in network.usages)

    def _build_sdk_type(self, cluster_name):
        return types.Cluster(name=cluster_name)


class ClusterNetwork(object):

    def __init__(self, cluster):
        self._cluster = cluster
        self._service = None

    def import_by_id(self, net_id):
        cluster_networks_service = self._cluster.service.networks_service()
        self._service = cluster_networks_service.service(net_id)

    def assign(self, dc_network):
        cluster_networks_service = self._cluster.service.networks_service()
        cluster_networks_service.add(dc_network.sdk_type)
        self._service = cluster_networks_service.service(dc_network.id)

    @property
    def usages(self):
        return self._service.get().usages

    @property
    def id(self):
        return self._service.get().id

    def set_usages(self, usages):
        network_sdk_type = self._service.get()
        network_sdk_type.usages = usages
        self._service.update(network_sdk_type)
