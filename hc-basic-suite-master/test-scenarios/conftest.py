#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

import pytest

from ost_utils import engine_object_names
from ost_utils import he_utils

from ost_utils.pytest import pytest_collection_modifyitems

from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.backend import *
from ost_utils.pytest.fixtures.defaults import *
from ost_utils.pytest.fixtures.deployment import deploy
from ost_utils.pytest.fixtures.deployment import run_scripts
from ost_utils.pytest.fixtures.deployment import set_sar_interval
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.env import *
from ost_utils.pytest.fixtures.network import *
from ost_utils.pytest.fixtures.node import *
from ost_utils.pytest.fixtures.sdk import *
from ost_utils.pytest.fixtures.storage import *
from ost_utils.pytest.running_time import *


@pytest.fixture(scope="session")
def ansible_vms_to_deploy(hosts_hostnames, ansible_by_hostname):  # pylint: disable=function-redefined
    return ansible_by_hostname(hosts_hostnames)


# hosted-engine suites use a separate storage VM, but use the management
# network for storage traffic. Override the relevant fixtures.

@pytest.fixture(scope="session")
def sd_iscsi_host_ips(storage_management_ips):  # pylint: disable=function-redefined
    return storage_management_ips


@pytest.fixture(scope="session")
def sd_nfs_host_storage_name(storage_hostname):  # pylint: disable=function-redefined
    return storage_hostname


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host(ansible_storage):  # pylint: disable=function-redefined
    return ansible_storage


# hosted-engine suites use the default cluster/dc names. Override.


@pytest.fixture(scope="session")
def ost_dc_name():  # pylint: disable=function-redefined
    return engine_object_names.DEFAULT_DC_NAME


@pytest.fixture(scope="session")
def ost_cluster_name():  # pylint: disable=function-redefined
    return engine_object_names.DEFAULT_CLUSTER_NAME


@pytest.fixture(scope="session")
def hostnames_to_add(ansible_host0, hosts_hostnames):  # pylint: disable=function-redefined
    return list(
        set(hosts_hostnames) -
        set([he_utils.host_name_running_he_vm(ansible_host0)])
    )


@pytest.fixture(scope="session")
def hostnames_to_reboot(hostnames_to_add):  # pylint: disable=function-redefined
    return hostnames_to_add


@pytest.fixture(scope="session")
def deploy_hosted_engine():  # pylint: disable=function-redefined
    return True
