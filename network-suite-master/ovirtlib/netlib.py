#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import collections
import contextlib
import time

from ovirtsdk4 import types

from .sdkentity import EntityCreationError
from .sdkentity import SDKSubEntity
from .sdkentity import SDKRootEntity


OVIRTMGMT = 'ovirtmgmt'


class MacAddrInUseError(Exception):
    pass


class MacPoolIsInFullCapacityError(Exception):
    pass


class ExternalProviderRequired(Exception):
    pass


class NetworkUsage(object):

    DEFAULT_ROUTE = types.NetworkUsage.DEFAULT_ROUTE
    DISPLAY = types.NetworkUsage.DISPLAY
    GLUSTER = types.NetworkUsage.GLUSTER
    MANAGEMENT = types.NetworkUsage.MANAGEMENT
    MIGRATION = types.NetworkUsage.MIGRATION
    VM = types.NetworkUsage.VM


class VnicInterfaceType(object):

    VIRTIO = types.NicInterface.VIRTIO


class Network(SDKSubEntity):
    @property
    def name(self):
        return self.get_sdk_type().name

    def create(
        self,
        name,
        vlan=None,
        usages=(NetworkUsage.VM,),
        qos=None,
        auto_generate_profile=True,
        external_provider=None,
        external_provider_physical_network=None,
        mtu=None,
        port_isolation=None,
    ):
        """
        :type name: string
        :type vlan: integer
        :type usages: (netlib.NetworkUsage,)
        :type qos: netlib.QoS
        :type auto_generate_profile: bool
        :type external_provider: providerlib.OpenStackNetworkProvider
        :type external_provider_physical_network: netlib.Network
        :type mtu: integer
        :type port_isolation: bool
        """
        qos_type = None if qos is None else qos.get_sdk_type()
        sdk_type = types.Network(
            name=name,
            data_center=self._parent_sdk_entity.service.get(),
            usages=usages,
            qos=qos_type,
            profile_required=auto_generate_profile,
            mtu=mtu,
            port_isolation=port_isolation,
        )
        if vlan is not None:
            sdk_type.vlan = types.Vlan(id=vlan)
        if external_provider is not None:
            sdk_type.external_provider = types.OpenStackNetworkProvider(id=external_provider.id)
        if external_provider_physical_network is not None:
            if external_provider is None:
                raise ExternalProviderRequired
            sdk_type.external_provider_physical_network = types.Network(id=external_provider_physical_network.id)
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, parent_entity):
        return parent_entity.service.networks_service()

    def labels(self):
        return self._system_network_service().network_labels_service().list()

    def vnic_profiles(self):
        profiles = self._system_network_service().vnic_profiles_service().list()
        vnic_profiles = []
        for profile in profiles:
            vnic_profile = VnicProfile(self.system)
            vnic_profile.import_by_id(profile.id)
            vnic_profiles.append(vnic_profile)
        return vnic_profiles

    def vnic_profile(self, name=None):
        """
        :param name: if no name is specified the default name for a vnic
        profile is assumed, which is the network name
        """
        profile_name = self.name if name is None else name
        return next(vnic_profile for vnic_profile in self.vnic_profiles() if vnic_profile.name == profile_name)

    def _system_network_service(self):
        return self.system.networks_service.network_service(self.id)

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'name:{self.name}, '
                f'qos:{self.get_sdk_type().qos}, '
                f'mtu:{self.get_sdk_type().mtu}, '
                f'vlan:{self.get_sdk_type().vlan}, '
                f'dc:{self._parent_sdk_entity}, '
                f'id:{self.id}>'
            )
        )

    @staticmethod
    def get_networks_ids(networks):
        """
        :param networks: []netlib.Network
        :return: frozenset(String)
        """
        return frozenset(network.id for network in networks)


class VnicProfile(SDKRootEntity):
    @property
    def name(self):
        return self.get_sdk_type().name

    def create(self, name, network, qos=None):
        qos_type = None if qos is None else qos.get_sdk_type()
        sdk_type = types.VnicProfile(name=name, network=network.get_sdk_type(), qos=qos_type)
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, sdk_system):
        return sdk_system.vnic_profiles_service

    @property
    def filter(self):
        sdk_network_filter = self.get_sdk_type().network_filter
        if sdk_network_filter:
            network_filter = NetworkFilter(self.system)
            network_filter.import_by_id(sdk_network_filter.id)
            return network_filter
        return None

    @filter.setter
    def filter(self, new_filter):
        new_filter_id = None if new_filter is None else new_filter.id
        new_sdk_filter = types.NetworkFilter(id=new_filter_id)
        self.update(network_filter=new_sdk_filter)

    @staticmethod
    def iterate(system):
        for sdk_obj in system.vnic_profiles_service.list():
            profile = VnicProfile(system)
            profile.import_by_id(sdk_obj.id)
            yield profile

    @property
    def custom_properties(self):
        sdk_custom_properties = self.service.get().custom_properties or []

        return [CustomProperty(p.name, p.value) for p in sdk_custom_properties]

    @custom_properties.setter
    def custom_properties(self, properties):
        service = self.service.get()
        service.custom_properties = [types.CustomProperty(name=p.name, value=p.value) for p in properties]
        self.service.update(service)

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'name:{self.name}, '
                f'filter:{self.filter}, '
                f'custom_props:{[(p.name, p.value) for p in self.custom_properties]}'
                f'id:{self.id}>'
            )
        )


class Vnic(SDKSubEntity):
    @property
    def name(self):
        return self.get_sdk_type().name

    @property
    def plugged(self):
        return self.get_sdk_type().plugged

    @property
    def linked(self):
        return self.get_sdk_type().linked

    @linked.setter
    def linked(self, linked):
        sdk_type = self.get_sdk_type()
        sdk_type.linked = linked
        self._service.update(sdk_type)

    @property
    def mac_address(self):
        return self.get_sdk_type().mac.address

    @mac_address.setter
    def mac_address(self, address):
        sdk_type = self.get_sdk_type()
        sdk_type.mac.address = address
        self._service.update(sdk_type)

    def create(
        self,
        name,
        vnic_profile,
        interface=VnicInterfaceType.VIRTIO,
        mac_addr=None,
    ):
        """
        :type name: string
        :type vnic_profile: netlib.VnicProfile
        :type interface: netlib.VnicInterfaceType
        :type mac_addr: string
        """

        sdk_type = types.Nic(
            name=name,
            interface=interface,
            vnic_profile=vnic_profile.get_sdk_type(),
        )
        if mac_addr is not None:
            sdk_type.mac = types.Mac(address=mac_addr)
        try:
            self._create_sdk_entity(sdk_type)
        except EntityCreationError as err:
            message = err.args[0]
            if 'MAC Address' in message and 'in use' in message:
                raise MacAddrInUseError(message)
            elif 'Not enough MAC addresses' in message:
                raise MacPoolIsInFullCapacityError(message)
            raise

    def hotunplug(self):
        self._service.deactivate()

    def hotplug(self):
        self._service.activate()

    def hot_replace_mac_addr(self, mac_addr):
        self.hotunplug()
        self.mac_address = mac_addr
        self.hotplug()

    def hot_replace_profile(self, profile):
        time.sleep(15)
        self.hotunplug()
        self.vnic_profile = profile
        time.sleep(15)
        self.hotplug()

    @contextlib.contextmanager
    def toggle_profile(self, profile):
        original_profile = self.vnic_profile
        self.hot_replace_profile(profile)
        try:
            yield
        finally:
            self.hot_replace_profile(original_profile)

    def _get_parent_service(self, parent_entity):
        return parent_entity.service.nics_service()

    @property
    def vnic_profile(self):
        sdk_profile = self.get_sdk_type().vnic_profile
        if sdk_profile is None:
            return EmptyVnicProfile()

        profile = VnicProfile(self._parent_sdk_entity._parent_sdk_system)
        profile.import_by_id(sdk_profile.id)
        return profile

    @vnic_profile.setter
    def vnic_profile(self, new_profile):
        sdk_nic = self.get_sdk_type()
        if sdk_nic.vnic_profile is None:
            sdk_nic.vnic_profile = new_profile.get_sdk_type()
        sdk_nic.vnic_profile.id = new_profile.id
        self.service.update(sdk_nic)

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'name:{self.name}, '
                f'linked:{self.linked}, '
                f'synced:{self.get_sdk_type().synced}, '
                f'plugged:{self.get_sdk_type().plugged}, '
                f'mac:{self.mac_address}, '
                f'id:{self.id}>'
            )
        )


class NetworkFilter(SDKRootEntity):
    @property
    def name(self):
        return self.get_sdk_type().name

    def _get_parent_service(self, sdk_system):
        return sdk_system.network_filters_service

    def create(self):
        raise NotImplementedError('oVirt connot create NetworkFilters')

    def __repr__(self):
        return self._execute_without_raising(lambda: f'<{self.__class__.__name__}| name:{self.name}, id:{self.id}>')


class QoS(SDKSubEntity):
    @property
    def name(self):
        return self.get_sdk_type().name

    def create(
        self,
        name,
        qos_type,
        inbound_average=None,
        inbound_peak=None,
        inbound_burst=None,
        outbound_average=None,
        outbound_peak=None,
        outbound_burst=None,
        outbound_average_upperlimit=None,
        outbound_average_realtime=None,
        outbound_average_linkshare=None,
    ):
        self._create_sdk_entity(
            types.Qos(
                name=name,
                type=qos_type,
                inbound_average=inbound_average,
                inbound_peak=inbound_peak,
                inbound_burst=inbound_burst,
                outbound_average=outbound_average,
                outbound_peak=outbound_peak,
                outbound_burst=outbound_burst,
                outbound_average_upperlimit=outbound_average_upperlimit,
                outbound_average_realtime=outbound_average_realtime,
                outbound_average_linkshare=outbound_average_linkshare,
            )
        )
        self.get_sdk_type().id = self.id

    def _get_parent_service(self, parent_entity):
        return parent_entity.service.qoss_service()


class EmptyVnicProfile(object):
    """
    Class needed to mimic the API behaviour.
    Engine defines an empty vnic profile by assigning no profile
    to the vnic.

    This class represents an empty API concrete type hidden
    behind the methods that are needed by other netlib
    classes.

    There are two flows thad needs to covered with
    this class:

    1. vnic creation with empty vnic does not need profile
    to be specified -> profile can be None or empty concrete
    sdk type

    2. vnic profile change into empty requires
    profile to be specified with None id
    """

    @property
    def id(self):
        return None

    def get_sdk_type(self):
        return types.VnicProfile()


@contextlib.contextmanager
def create_vnic_profile(system, name, network, qos=None):
    vnic_p = VnicProfile(system)
    vnic_p.create(name, network, qos)
    try:
        yield vnic_p
    finally:
        vnic_p.remove()


@contextlib.contextmanager
def new_network(name, dc, vlan=None, port_isolation=None):
    network = Network(dc)
    network.create(name=name, vlan=vlan, port_isolation=port_isolation)
    try:
        yield network
    finally:
        network.remove()


CustomProperty = collections.namedtuple('CustomProperty', ['name', 'value'])
