#
# Copyright 2020 Red Hat, Inc.
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

import abc

from ost_utils import memoized


class BaseBackend(abc.ABC):

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
    def ansible_inventory_str(self):
        """Returns a string with the contents of an ansible inventory for the VMs.

        Returns:
            str: Contents of an ansible inventory.

        """

    @abc.abstractmethod
    def artifacts(self):
        """Function returning a mapping of hostname --> list of artifacts

        Returns:
            dict: Hostname --> list of artifacts.

            Example value for basic suite:

            {
                'ost-basic-suite-master-engine': [
                    '/var/log',
                    '/var/cache/ovirt-engine',
                ],
                'ost-basic-suite-master-host-0': [
                    '/etc/resolv.conf',
                    '/var/log',
                ],
                'ost-basic-suite-master-host-1': [
                    '/etc/resolv.conf',
                    '/var/log',
                ]
            }

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

    def ifaces_for(self, hostname, network_name):
        return self.iface_mapping()[hostname][network_name]

    @memoized.memoized
    def hostnames(self):
        return set(self.iface_mapping().keys())

    @memoized.memoized
    def engine_hostname(self):
        return next(hn for hn in self.hostnames() if "engine" in hn)

    @memoized.memoized
    def hosts_hostnames(self):
        # The output should always be sorted, so we can refer by indices
        return sorted(hn for hn in self.hostnames() if "host" in hn)

    @memoized.memoized
    def storage_hostname(self):
        # Storage VM does not always exist - some suites do not define it
        return next((hn for hn in self.hostnames() if "storage" in hn), None)

    @memoized.memoized
    def network_names(self):
        return {
            network_name
            for mapping in self.iface_mapping().values()
            for network_name in mapping.keys()
        }

    @memoized.memoized
    def management_network_name(self):
        return next(nn for nn in self.network_names() if "management" in nn)

    @memoized.memoized
    def storage_network_name(self):
        return next(nn for nn in self.network_names() if "storage" in nn)

    @memoized.memoized
    def bonding_network_name(self):
        return next(nn for nn in self.network_names() if "bonding" in nn)

    @abc.abstractmethod
    def libvirt_net_name(self, net_name):
        pass
