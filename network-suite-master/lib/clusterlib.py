#
# Copyright 2017-2018 Red Hat, Inc.
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
import collections
import contextlib

from ovirtsdk4 import types

from lib import datacenterlib

from lib.sdkentity import SDKRootEntity
from lib.sdkentity import SDKSubEntity


MacPoolRange = collections.namedtuple("MacPoolRange", "start end")


class SwitchType():
    LEGACY = types.SwitchType.LEGACY
    OVS = types.SwitchType.OVS


@contextlib.contextmanager
def mac_pool(system, cluster, name, ranges, allow_duplicates=False):
    mac_pool_id = cluster.get_mac_pool().id

    temp_mac_pool = MacPool(system)
    temp_mac_pool.create(name, ranges, allow_duplicates)
    try:
        cluster.set_mac_pool(temp_mac_pool)
        yield temp_mac_pool
    finally:
        mac_pool = MacPool(system)
        mac_pool.import_by_id(mac_pool_id)

        cluster.set_mac_pool(mac_pool)
        temp_mac_pool.remove()


class MacPool(SDKRootEntity):

    def create(self, name, ranges, allow_duplicates=False):
        """
        :param name: string
        :param ranges: []MacPoolRange
        """
        sdk_type = types.MacPool(
            name=name,
            ranges=[types.Range(from_=r.start, to=r.end) for r in ranges],
            allow_duplicates=allow_duplicates
        )
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, system):
        return system.mac_pools_service


class Cluster(SDKRootEntity):

    @property
    def name(self):
        return self.get_sdk_type().name

    def create(self, data_center, cluster_name):
        sdk_type = types.Cluster(
            name=cluster_name,
            data_center=data_center.get_sdk_type()
        )
        self._create_sdk_entity(sdk_type)

    def get_mac_pool(self):
        mac_pool = MacPool(self._parent_sdk_system)
        mac_pool.import_by_id(self.get_sdk_type().mac_pool.id)
        return mac_pool

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

    @property
    def network_switch_type(self):
        return self.get_sdk_type().switch_type

    def set_network_switch_type(self, switch_type):
        self.update(switch_type=switch_type)

    def set_mac_pool(self, mac_pool):
        self.update(mac_pool=mac_pool.get_sdk_type())

    def _get_parent_service(self, system):
        return system.clusters_service


class ClusterNetwork(SDKSubEntity):

    def create(self):
        pass

    def assign(self, dc_network, required=False):
        sdk_type = dc_network.get_sdk_type()
        sdk_type.required = required

        self._parent_service.add(sdk_type)
        service = self._parent_service.service(dc_network.id)
        self._set_service(service)

    def _get_parent_service(self, cluster):
        return cluster.service.networks_service()

    @property
    def usages(self):
        return self.get_sdk_type().usages

    def set_usages(self, usages):
        self.update(usages=usages)
