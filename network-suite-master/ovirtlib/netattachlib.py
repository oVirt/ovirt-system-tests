#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

from ovirtsdk4 import types


class IpVersion(object):

    V4 = types.IpVersion.V4
    V6 = types.IpVersion.V6


class IpAssignment(object):
    def __init__(self, version, addr, mask, gateway=None, boot_protocol=None):
        self._ip = types.Ip(addr, gateway, mask, version)
        self._boot_protocol = boot_protocol

    @property
    def address(self):
        return self._ip.address

    @property
    def netmask(self):
        return self._ip.netmask

    @property
    def gateway(self):
        return self._ip.gateway

    @property
    def version(self):
        return self._ip.version

    @property
    def boot_protocol(self):
        return self._boot_protocol

    def __repr__(self):
        return (
            f'<{self.__class__.__name__}| '
            f'addr:{self.address}, '
            f'mask:{self.netmask}, '
            f'gw:{self.gateway}, '
            f'version:{self.version}, '
            f'boot_proto:{self._boot_protocol}>'
        )


class StaticIpv4Assignment(IpAssignment):
    def __init__(self, addr, mask, gateway=None, version=IpVersion.V4):
        super(StaticIpv4Assignment, self).__init__(version, addr, mask, gateway, types.BootProtocol.STATIC)


class StaticIpv6Assignment(IpAssignment):
    def __init__(self, addr, prefix, gateway=None, version=IpVersion.V6):
        super(StaticIpv6Assignment, self).__init__(version, addr, prefix, gateway, types.BootProtocol.STATIC)


NO_V4 = IpAssignment(IpVersion.V4, None, None, None, types.BootProtocol.NONE)
NO_V6 = IpAssignment(IpVersion.V6, None, None, None, types.BootProtocol.NONE)
IPV4_DHCP = IpAssignment(IpVersion.V4, None, None, None, types.BootProtocol.DHCP)
IPV6_POLY_DHCP_AUTOCONF = IpAssignment(IpVersion.V6, None, None, None, types.BootProtocol.POLY_DHCP_AUTOCONF)
DYNAMIC_IP_ASSIGN = {'inet': IPV4_DHCP, 'inet6': IPV6_POLY_DHCP_AUTOCONF}


class NetworkAttachmentData(object):
    def __init__(self, network, nic_name, ip_assignments=(), id=None, in_sync=True, nic_id=None):
        self._network = network
        self._nic_name = nic_name
        self._nic_id = nic_id
        self._ip_assignments = ip_assignments
        self._id = id
        self._in_sync = in_sync

    @property
    def network(self):
        return self._network

    @property
    def nic_name(self):
        return self._nic_name

    @property
    def nic_id(self):
        return self._nic_id

    @property
    def ip_assignments(self):
        return self._ip_assignments

    @property
    def id(self):
        return self._id

    @property
    def in_sync(self):
        return self._in_sync

    def to_network_attachment(self):
        """
        :param attachment_data: netattachlib.NetworkAttachmentData
        :return: types.NetworkAttachment
        """
        attachment = types.NetworkAttachment(
            network=self.network.get_sdk_type(),
            host_nic=types.HostNic(name=self.nic_name),
        )
        attachment.ip_address_assignments = self._to_ip_address_assignments(self.ip_assignments)
        attachment.id = self.id
        attachment.in_sync = self.in_sync
        return attachment

    def _to_ip_address_assignments(self, ip_assignments):
        """
        :param ip_assignments: list(netattachlib.IpAssignment)
        :return: list(types.IpAddressAssignment)
        """
        return [self._to_ip_address_assignment(ip_assignment) for ip_assignment in ip_assignments]

    def _to_ip_address_assignment(self, ip_assignment):
        """
        :param ip_assignment: netattachlib.IpAssignment
        :return: types.IpAddressAssignment
        """
        ip_address_assignment = types.IpAddressAssignment(
            assignment_method=ip_assignment.boot_protocol,
            ip=types.Ip(
                address=ip_assignment.address,
                netmask=ip_assignment.netmask,
                gateway=ip_assignment.gateway,
                version=ip_assignment.version,
            ),
        )
        return ip_address_assignment

    def set_ip_assignments(self, network_attachment):
        """
        :param network_attachment: types.NetworkAttachment
        """
        self._ip_assignments = self._to_ip_assignments(network_attachment.ip_address_assignments)

    def _to_ip_assignments(self, ip_address_assignments):
        """
        :param ip_address_assignments: list(types.IpAddressAssignment)
        :return: list(netattachlib.IpAssignment)
        """
        return [self._to_ip_assignment(ip_address_assignment) for ip_address_assignment in ip_address_assignments]

    def _to_ip_assignment(self, ip_address_assignment):
        """
        :param ip_address_assignment: types.IpAddressAssignment
        :return: netattachlib.IpAssignment
        """
        return IpAssignment(
            ip_address_assignment.ip.version,
            ip_address_assignment.ip.address,
            ip_address_assignment.ip.netmask,
            ip_address_assignment.ip.gateway,
            ip_address_assignment.assignment_method,
        )

    def __repr__(self):
        return (
            f'<{self.__class__.__name__}| '
            f'network:{self.network}, '
            f'nic_name:{self.nic_name}, '
            f'nic_id:{self.nic_id}, '
            f'in_sync:{self.in_sync}, '
            f'ip_assign:{self.ip_assignments}'
        )

    @staticmethod
    def to_network_attachments(network_attachments_data):
        """
        :param network_attachments_data: []netattachlib.NetworkAttachmentData
        :return: []types.NetworkAttachment
        """
        return [attachment.to_network_attachment() for attachment in network_attachments_data]


class BondingData(object):
    def __init__(self, name, slave_names, options={}):
        self._name = name
        self._options = options
        self._slave_names = slave_names

    @property
    def name(self):
        return self._name

    def to_bond(self):
        return types.HostNic(
            name=self._name,
            bonding=types.Bonding(options=self._sdk_options(), slaves=self._sdk_slaves()),
        )

    def _sdk_slaves(self):
        return [types.HostNic(name=name) for name in self._slave_names]

    def _sdk_options(self):
        return [types.Option(name=key, value=value) for key, value in self._options.items()]

    def __repr__(self):
        return (
            f'<{self.__class__.__name__}| '
            f'name:{self.name}, '
            f'options:{self._options}, '
            f'slaves:{self._slave_names}'
        )

    @staticmethod
    def get_bonds_names(bonds):
        """
        :param bonds: []netattachlib.BondingData
        :return:[]str
        """
        return [bond.name for bond in bonds]


class ActiveSlaveBonding(BondingData):
    def __init__(self, name, slave_names, options=None):
        options = options if options else {}
        options['mode'] = '1'
        super(ActiveSlaveBonding, self).__init__(name, slave_names, options)
