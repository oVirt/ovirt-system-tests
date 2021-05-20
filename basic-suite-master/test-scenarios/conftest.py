# -*- coding: utf-8 -*-
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

import pytest

from ost_utils.pytest import pytest_collection_modifyitems

from ost_utils.pytest.fixtures.ansible import ansible_all
from ost_utils.pytest.fixtures.ansible import ansible_by_hostname
from ost_utils.pytest.fixtures.ansible import ansible_clean_private_dirs
from ost_utils.pytest.fixtures.ansible import ansible_collect_logs
from ost_utils.pytest.fixtures.ansible import ansible_engine
from ost_utils.pytest.fixtures.ansible import ansible_host0
from ost_utils.pytest.fixtures.ansible import ansible_host1
from ost_utils.pytest.fixtures.ansible import ansible_inventory
from ost_utils.pytest.fixtures.ansible import ansible_storage

from ost_utils.pytest.fixtures.artifacts import artifacts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.artifacts import collect_artifacts

from ost_utils.pytest.fixtures.backend import all_hostnames
from ost_utils.pytest.fixtures.backend import backend
from ost_utils.pytest.fixtures.backend import backend_engine_hostname
from ost_utils.pytest.fixtures.backend import deploy_scripts
from ost_utils.pytest.fixtures.backend import host0_hostname
from ost_utils.pytest.fixtures.backend import host1_hostname
from ost_utils.pytest.fixtures.backend import hosts_hostnames

from ost_utils.pytest.fixtures.defaults import *

from ost_utils.pytest.fixtures.deployment import deploy
from ost_utils.pytest.fixtures.deployment import run_scripts

from ost_utils.pytest.fixtures.engine import *

from ost_utils.pytest.fixtures.env import suite_dir
from ost_utils.pytest.fixtures.env import working_dir

from ost_utils.pytest.fixtures.node import *

from ost_utils.pytest.fixtures.sdk import *

from ost_utils.pytest.fixtures.storage import *

from ost_utils.pytest.running_time import *


@pytest.fixture(scope="session")
def sd_iscsi_host_ips(engine_storage_ips):  # pylint: disable=function-redefined
    return engine_storage_ips


@pytest.fixture(scope="session")
def sd_nfs_host_storage_ip(engine_storage_ips):  # pylint: disable=function-redefined
    return engine_storage_ips[0]


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host(ansible_engine):  # pylint: disable=function-redefined
    return ansible_engine
