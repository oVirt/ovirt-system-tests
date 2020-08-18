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

from __future__ import absolute_import

"""Backend-specific information

This is the only module that should contain backend-specific
information. Every other part of OST code should be backend-agnostic.

ATM we only support lago, but the imports below should be adjusted
if new backends are available.

"""

# Functions returning specific network names
from ost_utils.backend.lago import management_network_name
from ost_utils.backend.lago import storage_network_name
from ost_utils.backend.lago import bonding_network_name

# Function returning a mapping of hostname --> networks --> ifaces, i.e.:
#
#{
#    'lago-basic-suite-master-engine': {
#        'lago-basic-suite-master-net-management': ['eth0'],
#        'lago-basic-suite-master-net-storage': ['eth1']
#    },
#    'lago-basic-suite-master-host-0': {
#        'lago-basic-suite-master-net-bonding': ['eth2', 'eth3'],
#        'lago-basic-suite-master-net-management': ['eth0'],
#        'lago-basic-suite-master-net-storage': ['eth1']
#    },
#     'lago-basic-suite-master-host-1': {
#        'lago-basic-suite-master-net-bonding': ['eth2', 'eth3'],
#        'lago-basic-suite-master-net-management': ['eth0'],
#        'lago-basic-suite-master-net-storage': ['eth1']
#    }
#}
from ost_utils.backend.lago import iface_mapping


def ifaces_for(hostname, network_name):
    return iface_mapping()[hostname][network_name]
