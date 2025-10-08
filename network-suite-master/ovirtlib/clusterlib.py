#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import collections
import contextlib

import ovirtsdk4
from ovirtsdk4 import types

from . import datacenterlib
from . import eventlib
from . import netlib
from . import syncutil

from .sdkentity import SDKRootEntity
from .sdkentity import SDKSubEntity


MacPoolRange = collections.namedtuple("MacPoolRange", "start end")


class MigrateMacPoolError(Exception):
    pass


class MacPoolContainsDuplicatesError(Exception):
    pass


class SwitchType:
    LEGACY = types.SwitchType.LEGACY
    OVS = types.SwitchType.OVS


@contextlib.contextmanager
def cluster(system, data_center, name):
    cluster = Cluster(system)
    cluster.create(data_center, name)
    try:
        yield cluster
    finally:
        cluster.remove()


@contextlib.contextmanager
def mac_pool(system, cluster, name, ranges, allow_duplicates=False):
    mac_pool_id = cluster.mac_pool.id

    temp_mac_pool = MacPool(system)
    temp_mac_pool.create(name, ranges, allow_duplicates)
    try:
        cluster.mac_pool = temp_mac_pool
        yield temp_mac_pool
    finally:
        mac_pool = MacPool(system)
        mac_pool.import_by_id(mac_pool_id)
        cluster.mac_pool = mac_pool

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
            allow_duplicates=allow_duplicates,
        )
        self._create_sdk_entity(sdk_type)

    def set_allow_duplicates(self, allow_duplicates):
        try:
            self.update(allow_duplicates=allow_duplicates)
        except ovirtsdk4.Error as err:
            message = err.args[0]
            if 'Cannot migrate MACs to another MAC pool' in message:
                raise MigrateMacPoolError(message)
            if 'mac pool contains duplicate macs' in message:
                raise MacPoolContainsDuplicatesError(message)
            raise

    def _get_parent_service(self, sdk_system):
        return sdk_system.mac_pools_service


class Cluster(SDKRootEntity):
    @property
    def name(self):
        return self.get_sdk_type().name

    def create(self, data_center, cluster_name):
        sdk_type = types.Cluster(name=cluster_name, data_center=data_center.get_sdk_type())
        self._create_sdk_entity(sdk_type)

    @property
    def mac_pool(self):
        mac_pool = MacPool(self.system)
        mac_pool.import_by_id(self.get_sdk_type().mac_pool.id)
        return mac_pool

    @mac_pool.setter
    def mac_pool(self, mac_pool):
        self.update(mac_pool=mac_pool.get_sdk_type())

    def get_data_center(self):
        dc = datacenterlib.DataCenter(self.system)
        dc.import_by_id(self.get_sdk_type().data_center.id)
        return dc

    def networks(self):
        networks = []
        for sdk_net in self._service.networks_service().list():
            cluster_network = ClusterNetwork(self)
            cluster_network.import_by_id(sdk_net.id)
            networks.append(cluster_network)
        return networks

    def host_ids(self):
        return [sdk_host.id for sdk_host in self.system.hosts_service.list() if sdk_host.cluster.id == self.id]

    def is_empty(self):
        return not self.host_ids()

    def mgmt_network(self):
        return next(network for network in self.networks() if types.NetworkUsage.MANAGEMENT in network.usages)

    @property
    def network_switch_type(self):
        return self.get_sdk_type().switch_type

    @network_switch_type.setter
    def network_switch_type(self, switch_type):
        self.update(switch_type=switch_type)

    def sync_all_networks(self):
        self.service.sync_all_networks()

    def remove(self):
        self.wait_until_empty()
        super(Cluster, self).remove()

    def wait_until_empty(self):
        self._report_is_empty('before')
        syncutil.sync(
            exec_func=self.is_empty,
            exec_func_args=(),
            success_criteria=lambda empty: empty,
        )
        self._report_is_empty('after')

    def _report_is_empty(self, when):
        eventlib.EngineEvents(self.system).add(f'OST - {when} wait until empty: cluster empty({self.is_empty()})')

    def _get_parent_service(self, sdk_system):
        return sdk_system.clusters_service

    @staticmethod
    def iterate(system):
        for sdk_obj in system.clusters_service.list():
            cluster = Cluster(system)
            cluster.import_by_id(sdk_obj.id)
            yield cluster

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'name:{self.name}, '
                f'switch:{self.network_switch_type}, '
                f'host ids:{self.host_ids()}, '
                f'id:{self.id}>'
            )
        )


class ClusterNetwork(SDKSubEntity):
    def create(self):
        pass

    def assign(self, dc_network, required=False):
        sdk_type = dc_network.get_sdk_type()
        sdk_type.required = required

        self._parent_service.add(sdk_type)
        service = self._parent_service.service(dc_network.id)
        self._set_service(service)

    def _get_parent_service(self, parent_entity):
        return parent_entity.service.networks_service()

    @property
    def usages(self):
        return self.get_sdk_type().usages

    def set_usages(self, usages):
        self.update(usages=usages)


@contextlib.contextmanager
def network_assignment(cluster, network, required=False):
    cluster_network = ClusterNetwork(cluster)
    cluster_network.assign(network, required)
    try:
        yield cluster_network
    finally:
        cluster_network.remove()


@contextlib.contextmanager
def new_assigned_network(name, data_center, cluster, vlan=None, port_isolation=None):
    with netlib.new_network(name, data_center, vlan, port_isolation) as network:
        with network_assignment(cluster, network):
            yield network
