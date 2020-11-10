# Copyright 2017-2020 Red Hat, Inc.
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
import logging
import os
import pytest
import shutil

from lago import sdk as lagosdk

from repo_server import create_repo_server

from fixtures.ansible import host0_facts  # NOQA: F401
from fixtures.ansible import host1_facts  # NOQA: F401
from fixtures.ansible import engine_facts  # NOQA: F401
from fixtures.ansible import ansible_engine  # NOQA: F401

from fixtures.cluster import default_cluster  # NOQA: F401

from fixtures.network import ovirtmgmt_network  # NOQA: F401
from fixtures.network import ovirtmgmt_vnic_profile  # NOQA: F401

from fixtures.host import host_0  # NOQA: F401
from fixtures.host import host_1  # NOQA: F401
from fixtures.host import host_0_up  # NOQA: F401
from fixtures.host import host_1_up  # NOQA: F401
from fixtures.host import install_hosts_to_save_time  # NOQA: F401

from fixtures.engine import engine_full_username  # NOQA: F401
from fixtures.engine import engine_password  # NOQA: F401
from fixtures.engine import engine_ssh_password  # NOQA: F401
from fixtures.engine import engine_ip  # NOQA: F401
from fixtures.engine import engine  # NOQA: F401
from fixtures.engine import api  # NOQA: F401
from fixtures.engine import test_invocation_logger  # NOQA: F401

from fixtures.fqdn import fqdn  # NOQA: F401
from fixtures.fqdn import engine_storage_ipv6  # NOQA: F401
from fixtures.fqdn import host0_eth1_ipv6  # NOQA: F401
from fixtures.fqdn import host0_eth2_ipv6  # NOQA: F401

from fixtures.storage import default_storage_domain  # NOQA: F401
from fixtures.storage import lun_id  # NOQA: F401

from fixtures.providers import ovirt_image_repo  # NOQA: F401

from fixtures.virt import cirros_template  # NOQA: F401

from fixtures.data_center import data_centers_service  # NOQA: F401
from fixtures.data_center import default_data_center  # NOQA: F401

from fixtures.system import system  # NOQA: F401

# Import OST utils fixtures
from ost_utils.pytest.fixtures.virt import cirros_image  # NOQA: F401
from ost_utils.pytest.fixtures.virt import (  # NOQA: F401
    transformed_cirros_image,
)

from testlib import suite


def pytest_addoption(parser):
    parser.addoption('--lago-env', action='store')
    parser.addoption('--artifacts-path', action='store')


@pytest.fixture(scope='session')
def artifacts_path():
    p = pytest.config.getoption(
        '--artifacts-path',
        default='exported_artifacts'
    )
    if os.path.isdir(p):
        shutil.rmtree(p)

    os.makedirs(p)

    return p


@pytest.fixture(scope='session')
def env(artifacts_path):
    workdir = pytest.config.getoption('--lago-env')
    lago_log_path = os.path.join(workdir, 'default/logs/lago.log')
    lago_env = lagosdk.load_env(
        workdir=workdir,
        logfile=lago_log_path,
        loglevel=logging.DEBUG
    )

    # When OST is run over an el8 distro the repo server is no longer
    # required due to the introduction of prebuilt ost-images. But when OST is
    # run over an el7 distro, the repo server is still required.
    use_repo_server = os.environ.get("USE_LAGO_OST_PLUGIN", "0") == "1"
    try:
        if use_repo_server:
            repo_server = create_repo_server(workdir, lago_env)
        yield lago_env
    finally:
        if use_repo_server:
            repo_server.shutdown()
        shutil.move(lago_log_path, artifacts_path)


@pytest.fixture(scope='module', autouse=True)
def collect_artifacts(env, artifacts_path, request):
    with suite.collect_artifacts(env, artifacts_path, request.module.__name__):
        yield
