#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import ipaddress

import pytest


@pytest.fixture(scope="session")
def management_network_name(backend):
    return backend.management_network_name()


@pytest.fixture(scope="session")
def management_subnet(backend, tested_ip_version):
    return backend.management_subnet(tested_ip_version)


@pytest.fixture(scope="session")
def storage_network_name(backend):
    return backend.storage_network_name()


@pytest.fixture(scope="session")
def storage_subnet(backend, tested_ip_version):
    return backend.storage_subnet(tested_ip_version)


@pytest.fixture(scope="session")
def bonding_network_name(backend):
    return backend.bonding_network_name()


@pytest.fixture(scope="session")
def bonding_subnet(backend, tested_ip_version):
    return backend.bonding_subnet(tested_ip_version)


@pytest.fixture(scope="session")
def management_gw_ip(engine_ip):
    # TODO: retrieve gateway addresses from the backend directly
    prefix_len = 64 if ipaddress.ip_address(engine_ip).version == 6 else 24
    return str(ipaddress.ip_interface(f"{engine_ip}/{prefix_len}").network[1])
