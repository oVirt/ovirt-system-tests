#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

import pytest

from ost_utils.pytest import pytest_collection_modifyitems

from ost_utils.pytest.fixtures.artifacts import *
from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.backend import *
from ost_utils.pytest.fixtures.defaults import *
from ost_utils.pytest.fixtures.deployment import deploy
from ost_utils.pytest.fixtures.deployment import run_scripts
from ost_utils.pytest.fixtures.deployment import set_sar_interval
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.env import *
from ost_utils.pytest.fixtures.he import *
from ost_utils.pytest.fixtures.network import *
from ost_utils.pytest.fixtures.node import *
from ost_utils.pytest.fixtures.sdk import *
from ost_utils.pytest.fixtures.storage import *
from ost_utils.pytest.running_time import *


@pytest.fixture(scope="session")
def sd_iscsi_host_ip(engine_storage_ips):  # pylint: disable=function-redefined
    return engine_storage_ips[0]


@pytest.fixture(scope="session")
def sd_nfs_host_storage_name(engine_hostname):  # pylint: disable=function-redefined
    return engine_hostname


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host(ansible_engine):  # pylint: disable=function-redefined
    return ansible_engine


@pytest.fixture(scope="session")
def is_node_suite():  # pylint: disable=function-redefined
    return True
