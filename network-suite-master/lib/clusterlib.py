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

from lib import datacenterlib

from lib.sdkentity import SDKRootEntity
from lib.sdkentity import SDKSubEntity


class Cluster(SDKRootEntity):

    @property
    def name(self):
        return self.get_sdk_type().name

    def get_data_center(self):
        dc = datacenterlib.DataCenter(self._parent_sdk_system)
        dc.import_by_id(self.get_sdk_type().data_center.id)
        return dc

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

    def _get_parent_service(self, system):
        return system.clusters_service


class ClusterNetwork(SDKSubEntity):

    def assign(self, dc_network, required=False):
        sdk_type = dc_network.get_sdk_type()
        sdk_type.required = required

        self._parent_service.add(sdk_type)
        service = self._parent_service.service(dc_network.id)
        self._set_service(service)

    def _build_sdk_type(self, *args, **kwargs):
        pass

    def _get_parent_service(self, cluster):
        return cluster.service.networks_service()

    @property
    def usages(self):
        return self.get_sdk_type().usages

    def set_usages(self, usages):
        self.update(usages=usages)
