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
import random
import tempfile

import pytest

from ost_utils.ansible import facts
from ost_utils.backend.virsh import network

from ost_utils.pytest.fixtures.backend import backend


@pytest.fixture(scope="session")
def he_mac_address():
    return '54:52:{}'.format(
        ':'.join(('{:02x}'.format(random.randrange(255)) for i in range(4)))
    )


# FIXME this is not a good idea when there are multiple networks currently, as
# the ansible_default_ipv4 returns IP form a random gateway, and currently all
# OST networks result in a gateway for that particular network. It should return
# IP on the management network only
@pytest.fixture(scope="session")
def he_ipv4_address(ansible_host0_facts):
    host0_ipv4 = ansible_host0_facts.get('ansible_default_ipv4').get('address')
    return '{prefix}.{suffix}'.format(
        prefix='.'.join(host0_ipv4.split('.')[:3]),
        suffix=random.randrange(50, 100),
    )


# FIXME this is not a good idea when there are multiple networks currently, as
# the ansible_default_ipv6 returns IP form a random gateway, and currently all
# OST networks result in a gateway for that particular network. It should return
# IP on the management network only
@pytest.fixture(scope="session")
def he_ipv6_address(ansible_host0_facts):
    host0_ipv6 = ansible_host0_facts.get('ansible_default_ipv6').get('address')
    *prefix, lasthextet = host0_ipv6.split(':')
    return '{prefix}:{prelast}63'.format(
        prefix=':'.join(prefix),
        prelast=lasthextet[:2],
    )


@pytest.fixture(scope="session")
def he_host_name(backend):
    return '{}-engine'.format(
        '-'.join(backend.storage_hostname().split('-')[:-1])
    )


@pytest.fixture(scope="session")
def ansible_he(
    management_network_name,
    ansible_inventory,
    backend,
    he_mac_address,
    he_ipv4_address,
    he_ipv6_address,
    he_host_name,
    ansible_by_hostname,
):
    network.add_name(
        libvirt_net_name=backend.libvirt_net_name(management_network_name),
        host_name=he_host_name,
        mac_address=he_mac_address,
        ipv4_address=he_ipv4_address,
        ipv6_address=he_ipv6_address,
    )
    ssh_key_file = os.environ.get('OST_IMAGES_SSH_KEY')
    ansible_inventory.add(
        he_host_name,
        (
            '[default]\n'
            f'{he_host_name} '
            f'ansible_host={he_ipv4_address} '
            f'ansible_ssh_private_key_file={ssh_key_file}\n'
        ).encode()
    )
    return ansible_by_hostname(he_host_name)


@pytest.fixture(scope="session")
def ansible_he_facts(ansible_he):
    return facts.Facts(ansible_he)
