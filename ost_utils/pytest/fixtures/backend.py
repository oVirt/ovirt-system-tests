#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

import os

import pytest

from ost_utils.backend import virsh


@pytest.fixture(scope="session")
def backend():
    return virsh.VirshBackend(os.environ["OST_DEPLOYMENT"])


@pytest.fixture(scope="session")
def deploy_scripts(backend):
    return backend.deploy_scripts()


@pytest.fixture(scope="session")
def backend_engine_hostname(backend):
    return backend.engine_hostname()


@pytest.fixture(scope="session")
def all_hostnames(backend):
    return backend.hostnames()


@pytest.fixture(scope="session")
def hosts_hostnames(backend):
    return backend.hosts_hostnames()


@pytest.fixture(scope="session")
def host0_hostname(hosts_hostnames):
    return hosts_hostnames[0]


@pytest.fixture(scope="session")
def host1_hostname(hosts_hostnames):
    return hosts_hostnames[1]


@pytest.fixture(scope="session")
def storage_hostname(backend):
    return backend.storage_hostname()


@pytest.fixture(scope="session")
def management_network_supports_ipv4(backend):
    return backend.management_network_supports_version(4)


@pytest.fixture(scope="session")
def tested_ip_version(backend):
    return 6 if backend.management_network_supports_version(6) else 4
