#
# Copyright 2020-2021 Red Hat, Inc.
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

import ipaddress

import pytest


@pytest.fixture(scope="session")
def management_network_name(backend):
    return backend.management_network_name()


@pytest.fixture(scope="session")
def storage_network_name(backend):
    return backend.storage_network_name()


@pytest.fixture(scope="session")
def bonding_network_name(backend):
    return backend.bonding_network_name()


@pytest.fixture(scope="session")
def management_gw_ip(engine_ip):
    # TODO: retrieve gateway addresses from the backend directly
    prefix_len = 64 if ipaddress.ip_address(engine_ip).version == 6 else 24
    return str(ipaddress.ip_interface(f"{engine_ip}/{prefix_len}").network[1])
