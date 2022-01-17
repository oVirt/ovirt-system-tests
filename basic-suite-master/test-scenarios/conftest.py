# -*- coding: utf-8 -*-
#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

import pytest

from ost_utils import network_utils

from ost_utils.pytest import pytest_collection_modifyitems

from ost_utils.pytest.fixtures.ansible import ansible_all
from ost_utils.pytest.fixtures.ansible import ansible_by_hostname
from ost_utils.pytest.fixtures.ansible import ansible_clean_private_dirs
from ost_utils.pytest.fixtures.ansible import ansible_collect_logs
from ost_utils.pytest.fixtures.ansible import ansible_engine
from ost_utils.pytest.fixtures.ansible import ansible_engine_facts
from ost_utils.pytest.fixtures.ansible import ansible_host0
from ost_utils.pytest.fixtures.ansible import ansible_host1
from ost_utils.pytest.fixtures.ansible import ansible_hosts
from ost_utils.pytest.fixtures.ansible import ansible_inventory
from ost_utils.pytest.fixtures.ansible import ansible_storage

from ost_utils.pytest.fixtures.artifacts import artifacts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.artifacts import artifact_list
from ost_utils.pytest.fixtures.artifacts import collect_artifacts
from ost_utils.pytest.fixtures.artifacts import collect_vdsm_coverage_artifacts
from ost_utils.pytest.fixtures.artifacts import dump_dhcp_leases
from ost_utils.pytest.fixtures.artifacts import generate_sar_stat_plots

from ost_utils.pytest.fixtures.backend import all_hostnames
from ost_utils.pytest.fixtures.backend import backend
from ost_utils.pytest.fixtures.backend import backend_engine_hostname
from ost_utils.pytest.fixtures.backend import deploy_scripts
from ost_utils.pytest.fixtures.backend import host0_hostname
from ost_utils.pytest.fixtures.backend import host1_hostname
from ost_utils.pytest.fixtures.backend import hosts_hostnames
from ost_utils.pytest.fixtures.backend import management_network_supports_ipv4

from ost_utils.pytest.fixtures.defaults import *

from ost_utils.pytest.fixtures.deployment import deploy
from ost_utils.pytest.fixtures.deployment import run_scripts
from ost_utils.pytest.fixtures.deployment import set_sar_interval

from ost_utils.pytest.fixtures.engine import *

from ost_utils.pytest.fixtures.env import ost_images_distro
from ost_utils.pytest.fixtures.env import root_dir
from ost_utils.pytest.fixtures.env import ssh_key_file
from ost_utils.pytest.fixtures.env import suite_dir
from ost_utils.pytest.fixtures.env import working_dir

from ost_utils.pytest.fixtures.network import management_gw_ip

from ost_utils.pytest.fixtures.node import *

from ost_utils.pytest.fixtures.sdk import *

from ost_utils.pytest.fixtures.storage import *

from ost_utils.pytest.running_time import *


@pytest.fixture(scope="session")
def sd_iscsi_host_ip(
    engine_storage_ips,
):  # pylint: disable=function-redefined
    return engine_storage_ips[0]


@pytest.fixture(scope="session")
def sd_nfs_host_storage_name(
    engine_hostname,
):  # pylint: disable=function-redefined
    return engine_hostname


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host(
    ansible_engine,
):  # pylint: disable=function-redefined
    return ansible_engine
