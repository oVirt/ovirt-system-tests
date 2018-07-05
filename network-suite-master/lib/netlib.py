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
import contextlib

from ovirtsdk4 import types

from lib.sdkentity import EntityCreationError
from lib.sdkentity import SDKSubEntity
from lib.sdkentity import SDKRootEntity


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


class IpVersion(object):

    V4 = types.IpVersion.V4
    V6 = types.IpVersion.V6


DYNAMIC_IP_CONFIG = [
    types.IpAddressAssignment(assignment_method=types.BootProtocol.DHCP),
    types.IpAddressAssignment(assignment_method=types.BootProtocol.DHCP,
                              ip=types.Ip(version=IpVersion.V6))
]


class VnicInterfaceType(object):

    VIRTIO = types.NicInterface.VIRTIO


def create_static_ip_config_assignment(addr, mask, gateway=None,
                                       version=IpVersion.V4):
    ip = types.Ip(address=addr, netmask=mask,
                  version=version, gateway=gateway)
    return types.IpAddressAssignment(
        assignment_method=types.BootProtocol.STATIC, ip=ip)


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


class Vnic(SDKSubEntity):

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


@contextlib.contextmanager
def create_vnic_profile(system, name, network, qos=None):
    vnic_p = VnicProfile(system)
    vnic_p.create(name, network, qos)
    try:
        yield vnic_p
    finally:
        vnic_p.remove()
