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
                'lago-basic-suite-master-engine': {
                    'lago-basic-suite-master-net-management': ['eth0'],
                    'lago-basic-suite-master-net-storage': ['eth1']
                },
                'lago-basic-suite-master-host-0': {
                    'lago-basic-suite-master-net-bonding': ['eth2', 'eth3'],
                    'lago-basic-suite-master-net-management': ['eth0'],
                    'lago-basic-suite-master-net-storage': ['eth1']
                },
                 'lago-basic-suite-master-host-1': {
                    'lago-basic-suite-master-net-bonding': ['eth2', 'eth3'],
                    'lago-basic-suite-master-net-management': ['eth0'],
                    'lago-basic-suite-master-net-storage': ['eth1']
                }
            }

        """

    @abc.abstractmethod
    def ansible_inventory(self):
        """Returns a path to a file containing ansible inventory for the VMs.

        The file should be deleted after the deriving class is garbage
        collected.

        Returns:
            str: Path to ansible inventory file.

        """

    def ifaces_for(self, hostname, network_name):
        return self.iface_mapping()[hostname][network_name]

    @memoized.memoized
    def hostnames(self):
        return set(self.iface_mapping().keys())

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
