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

import os
import tempfile

import pytest

from ost_utils.ansible import facts
from ost_utils.backend.virsh import network

from ost_utils.pytest.fixtures.backend import backend

# lago uses a simple scheme to do 1-1 mapping of IPv4 address
# to MAC address and to IPv6 address. So in theory we could have
# only the IPv4 address hard-coded and have the others calculated -
# either calling lago (internal?) functions or duplicating here the
# calculation. But I think hard-coding everything is enough in this
# case, and also makes it much easier to grep for stuff later.
# As-is, the constants below match what lago would have done when supplied
# with only the IPv4 address 192.168.200.99 and calculating IPv6 and MAC
# based on it. In principle, since we now do not rely on lago for this,
# we could use other random addresses. TODO: generalize this, also for
# allowing to run more than one copy of OST on the same machine (so at
# least one copy will not be able to use 192.168.200), and perhaps also
# allow doing this completely random - just pick a random MAC address,
# let dhcp (libvirt) allocate appropriate IPv4/IPv6 addresses based on
# the subnet, and use that.

@pytest.fixture(scope="session")
def he_mac_address():
    # This is also hard-coded in the answerfile. TODO: de-duplicate
    return '54:52:c0:a8:c8:63'


@pytest.fixture(scope="session")
def he_ipv4_address():
    return '192.168.200.99'


@pytest.fixture(scope="session")
def he_ipv6_address():
    return 'fd8f:1391:3a82:200::c0a8:c863'


@pytest.fixture(scope="session")
def he_host_name(backend):
    return '{}-engine'.format(
        '-'.join(backend.storage_hostname().split('-')[:-1])
    )


@pytest.fixture(scope="session", autouse=True)
def ansible_he(
    management_network_name,
    ansible_inventory,
    backend,
    he_mac_address,
    he_ipv4_address,
    he_ipv6_address,
    he_host_name,
    working_dir,
    ansible_by_hostname,
):
    network.add_name(
        libvirt_net_name=backend.libvirt_net_name(management_network_name),
        host_name=he_host_name,
        mac_address=he_mac_address,
        ipv4_address=he_ipv4_address,
        ipv6_address=he_ipv6_address,
    )
    ansible_inventory.add(
        he_host_name,
        (
            '[default]\n'
            f'{he_host_name} '
            f'ansible_host={he_ipv4_address} '
            f'ansible_ssh_private_key_file={working_dir}/current/id_rsa\n'
        ).encode()
    )
    return ansible_by_hostname(he_host_name)


@pytest.fixture(scope="session")
def ansible_he_facts(ansible_he):
    return facts.Facts(ansible_he)
