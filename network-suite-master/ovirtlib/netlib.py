#
# Copyright 2017-2019 Red Hat, Inc.
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

from ovirtlib.sdkentity import EntityCreationError
from ovirtlib.sdkentity import SDKSubEntity
from ovirtlib.sdkentity import SDKRootEntity


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

    def create(self,
               name,
               vlan=None,
               usages=(NetworkUsage.VM,),
               qos=None,
               auto_generate_profile=True,
               external_provider=None,
               external_provider_physical_network=None,
               mtu=None):
        """
        :type name: string
        :type vlan: integer
        :type usages: (netlib.NetworkUsage,)
        :type qos: netlib.QoS
        :type auto_generate_profile: bool
        :type external_provider: providerlib.OpenStackNetworkProvider
        :type external_provider_physical_network: netlib.Network
        :type mtu: integer
        """
        qos_type = None if qos is None else qos.get_sdk_type()
        sdk_type = types.Network(
            name=name,
            data_center=self._parent_sdk_entity.service.get(),
            usages=usages,
            qos=qos_type,
            profile_required=auto_generate_profile,
            mtu=mtu
        )
        if vlan is not None:
            sdk_type.vlan = types.Vlan(id=vlan)
        if external_provider is not None:
            sdk_type.external_provider = types.OpenStackNetworkProvider(
                id=external_provider.id)
        if external_provider_physical_network is not None:
            if external_provider is None:
                raise ExternalProviderRequired
            sdk_type.external_provider_physical_network = types.Network(
                id=external_provider_physical_network.id)
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, dc):
        return dc.service.networks_service()


class VnicProfile(SDKRootEntity):

    @property
    def name(self):
        return self.get_sdk_type().name

    def create(self, name, network, qos=None):
        qos_type = None if qos is None else qos.get_sdk_type()
        sdk_type = types.VnicProfile(
            name=name,
            network=network.get_sdk_type(),
            qos=qos_type
        )
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, system):
        return system.vnic_profiles_service

    def filter_id(self):
        network_filter = self.get_sdk_type().network_filter
        if network_filter:
            return network_filter.id
        return None

    @staticmethod
    def iterate(system):
        for sdk_obj in system.vnic_profiles_service.list():
            profile = VnicProfile(system)
            profile.import_by_id(sdk_obj.id)
            yield profile

    @property
    def custom_properties(self):
        sdk_custom_properties = self.service.get().custom_properties or []

        return [
            CustomProperty(p.name, p.value) for p in sdk_custom_properties]

    @custom_properties.setter
    def custom_properties(self, properties):
        service = self.service.get()
        service.custom_properties = [
            types.CustomProperty(name=p.name, value=p.value)
            for p in properties]
        self.service.update(service)


class Vnic(SDKSubEntity):

    @property
    def name(self):
        return self.get_sdk_type().name

    @property
    def linked(self):
        return self.get_sdk_type().linked

    def set_mac_addr(self, address):
        sdk_type = self.get_sdk_type()
        sdk_type.mac.address = address
        self._service.update(sdk_type)

    def set_linked(self, linked):
        sdk_type = self.get_sdk_type()
        sdk_type.linked = linked
        self._service.update(sdk_type)

    @property
    def mac_address(self):
        return self.get_sdk_type().mac.address

    def create(self, name, vnic_profile,
               interface=VnicInterfaceType.VIRTIO, mac_addr=None):
        """
        :type name: string
        :type vnic_profile: netlib.VnicProfile
        :type interface: netlib.VnicInterfaceType
        :type mac_addr: string
        """

        sdk_type = types.Nic(
            name=name,
            interface=interface,
            vnic_profile=vnic_profile.get_sdk_type()
        )
        if mac_addr is not None:
            sdk_type.mac = types.Mac(address=mac_addr)
        try:
            self._create_sdk_entity(sdk_type)
        except EntityCreationError as err:
            if 'MAC Address' in err.message and 'in use' in err.message:
                raise MacAddrInUseError(err.message)
            elif 'Not enough MAC addresses' in err.message:
                raise MacPoolIsInFullCapacityError(err.message)
            raise

    def hotunplug(self):
        self._service.deactivate()

    def hotplug(self):
        self._service.activate()

    def _get_parent_service(self, vm):
        return vm.service.nics_service()

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


class QoS(SDKSubEntity):

    @property
    def name(self):
        return self.get_sdk_type().name

    def create(self,
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
               outbound_average_linkshare=None):
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
                outbound_average_linkshare=outbound_average_linkshare
            )
        )
        self.get_sdk_type().id = self.id

    def _get_parent_service(self, dc):
        return dc.service.qoss_service()


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
def new_network(name, dc):
    network = Network(dc)
    network.create(name=name)
    try:
        yield network
    finally:
        network.remove()


CustomProperty = collections.namedtuple('CustomProperty', ['name', 'value'])
