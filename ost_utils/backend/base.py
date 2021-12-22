#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import abc
from functools import cache


class BaseBackend(abc.ABC):

    # DEPRECATED
    @abc.abstractmethod
    def iface_mapping(self):
        """Function returning a mapping of hostname --> networks --> ifaces

        Returns:
            dict: Hostname --> networks --> ifaces.

            Example value for basic suite:

            {
                'ost-basic-suite-master-engine': {
                    'lago-basic-suite-master-net-management': ['eth0'],
                    'lago-basic-suite-master-net-storage': ['eth1']
                },
                'ost-basic-suite-master-host-0': {
                    'lago-basic-suite-master-net-bonding': ['eth2', 'eth3'],
                    'lago-basic-suite-master-net-management': ['eth0'],
                    'lago-basic-suite-master-net-storage': ['eth1']
                },
                 'ost-basic-suite-master-host-1': {
                    'lago-basic-suite-master-net-bonding': ['eth2', 'eth3'],
                    'lago-basic-suite-master-net-management': ['eth0'],
                    'lago-basic-suite-master-net-storage': ['eth1']
                }
            }

        """

    @abc.abstractmethod
    def ip_mapping(self):
        """Function returning a mapping of hostname --> networks --> ips

        Returns:
            dict: Hostname --> networks --> ips.

            Example value:

            {
                'ost-basic-suite-master-engine': {
                    'management': [
                        IPv4Address('192.168.200.2'),
                        IPv6Address('fd8f:1391:3a82:150::c0a8:9602')
                    ],
                    'storage': [
                        IPv4Address('192.168.201.2'),
                        IPv6Address('fd8f:1391:3a82:150::c0a9:9603')
                    ]
                },
                'ost-basic-suite-master-host-0': {
                    ...
                }
            }

        """

    @abc.abstractmethod
    def ansible_inventory_str(self):
        """Returns a string with the contents of an ansible inventory for the VMs.

        Returns:
            str: Contents of an ansible inventory.

        """

    @abc.abstractmethod
    def deploy_scripts(self):
        """Function returning a mapping of hostname --> list of deploy scripts.

        Returns:
            dict: Hostname --> list of deploy scripts.

            Example value for basic suite:

            {
                'ost-basic-suite-master-engine': [
                    'common/deploy-scripts/setup_sar_stat.sh',
                    'common/deploy-scripts/setup_engine.sh',
                ],
                'ost-basic-suite-master-host-0': [
                    'common/deploy-scripts/setup_sar_stat.sh',
                    'common/deploy-scripts/setup_host.sh',
                ],
                'ost-basic-suite-master-host-1': [
                    'common/deploy-scripts/setup_sar_stat.sh',
                    'common/deploy-scripts/setup_host.sh',
                ]
            }

        """

    @abc.abstractmethod
    def libvirt_net_name(self, ost_net_name):
        """Function that finds the libvirt network name corresponding to the
         specified ost network name
        :param ost_net_name: String
        :return: String
        """

    @abc.abstractmethod
    def get_ip_prefix_for_management_network(self, ip_version):
        """Function that finds prefix of management network corresponding to
        the specified ip version
        :param ip_version: Int
        :return: Int
        """

    # DEPRECATED
    def ifaces_for(self, hostname, network_name):
        return self.iface_mapping()[hostname][network_name]

    def ips_for(self, hostname, network_name):
        return self.ip_mapping()[hostname][network_name]

    @cache
    def hostnames(self):
        return set(self.ip_mapping().keys())

    @cache
    def engine_hostname(self):
        return next(hn for hn in self.hostnames() if "engine" in hn)

    @cache
    def hosts_hostnames(self):
        # The output should always be sorted, so we can refer by indices
        return sorted(hn for hn in self.hostnames() if "host" in hn)

    @cache
    def storage_hostname(self):
        # Storage VM does not always exist - some suites do not define it
        return next((hn for hn in self.hostnames() if "storage" in hn), None)

    @cache
    def network_names(self):
        return {network_name for mapping in self.ip_mapping().values() for network_name in mapping.keys()}

    @cache
    def management_network_name(self):
        return next(nn for nn in self.network_names() if "management" in nn)

    @cache
    def storage_network_name(self):
        return next(nn for nn in self.network_names() if "storage" in nn)

    @cache
    def bonding_network_name(self):
        return next(nn for nn in self.network_names() if "bonding" in nn)

    @cache
    def management_network_supports_version(self, ip_version):
        return any(
            ip.version == ip_version for ip in list(self.ip_mapping().values())[0][self.management_network_name()]
        )

    @abc.abstractmethod
    def management_subnet(self, ip_version):
        """
        :param ip_version: 4 or 6
        :return: ipaddress.ip_network with the subnet address of the network
        """

    @abc.abstractmethod
    def bonding_subnet(self, ip_version):
        """
        :param ip_version: 4 or 6
        :return: ipaddress.ip_network with the subnet address of the network
        """

    @abc.abstractmethod
    def storage_subnet(self, ip_version):
        """
        :param ip_version: 4 or 6
        :return: ipaddress.ip_network with the subnet address of the network
        """
