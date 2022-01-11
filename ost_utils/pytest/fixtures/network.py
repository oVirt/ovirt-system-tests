#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

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
def management_gw_ip(backend, tested_ip_version):
    return backend.get_gw_ip_for_management_network(tested_ip_version)
