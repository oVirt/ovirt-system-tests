#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

import pytest

from ost_utils import engine_object_names
from ost_utils.pytest.fixtures.backend import backend
from ost_utils.pytest.fixtures.backend import hosts_hostnames


@pytest.fixture(scope="session")
def ost_dc_name():
    return engine_object_names.TEST_DC_NAME


@pytest.fixture(scope="session")
def ost_cluster_name():
    return engine_object_names.TEST_CLUSTER_NAME


@pytest.fixture(scope="session")
def hostnames_to_add(hosts_hostnames):
    return hosts_hostnames


@pytest.fixture(scope="session")
def hostnames_to_reboot(hosts_hostnames):
    return hosts_hostnames[:1]


@pytest.fixture(scope="session")
def deploy_hosted_engine():
    return False


@pytest.fixture(scope="session")
def ansible_vms_to_deploy(ansible_all):
    return ansible_all
