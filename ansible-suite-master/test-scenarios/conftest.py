#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import pytest

from ost_utils.pytest.fixtures.ansible import *

from ost_utils.pytest.fixtures.artifacts import artifacts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.artifacts import artifact_list
from ost_utils.pytest.fixtures.artifacts import collect_artifacts
from ost_utils.pytest.fixtures.artifacts import dump_dhcp_leases
from ost_utils.pytest.fixtures.artifacts import generate_sar_stat_plots

from ost_utils.pytest.fixtures.backend import all_hostnames
from ost_utils.pytest.fixtures.ansible import ansible_engine
from ost_utils.pytest.fixtures.ansible import ansible_inventory
from ost_utils.pytest.fixtures.backend import backend
from ost_utils.pytest.fixtures.backend import backend_engine_hostname
from ost_utils.pytest.fixtures.backend import deploy_scripts
from ost_utils.pytest.fixtures.backend import host0_hostname
from ost_utils.pytest.fixtures.backend import host1_hostname
from ost_utils.pytest.fixtures.backend import hosts_hostnames
from ost_utils.pytest.fixtures.backend import management_network_supports_ipv4
from ost_utils.pytest.fixtures.backend import storage_hostname

from ost_utils.pytest.fixtures.defaults import ansible_vms_to_deploy
from ost_utils.pytest.fixtures.defaults import hostnames_to_add

from ost_utils.pytest.fixtures.deployment import deploy
from ost_utils.pytest.fixtures.deployment import run_scripts
from ost_utils.pytest.fixtures.deployment import set_sar_interval

from ost_utils.pytest.fixtures.engine import *

from ost_utils.pytest.fixtures.env import ost_images_distro
from ost_utils.pytest.fixtures.env import root_dir
from ost_utils.pytest.fixtures.env import ssh_key_file
from ost_utils.pytest.fixtures.env import suite_dir
from ost_utils.pytest.fixtures.env import working_dir

from ost_utils.pytest.fixtures.storage import *


@pytest.fixture(scope="session")
def sd_iscsi_host_ip(
    storage_management_ips,
):  # pylint: disable=function-redefined
    return storage_management_ips[0]


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host(
    ansible_storage,  # noqa: F811
):  # pylint: disable=function-redefined
    return ansible_storage
