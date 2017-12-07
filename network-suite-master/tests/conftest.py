# Copyright 2017 Red Hat, Inc.
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

from lago import sdk as lagosdk

from repo_server import create_repo_server

from fixtures.cluster import clusters_service  # NOQA: F401
from fixtures.cluster import default_cluster  # NOQA: F401

from fixtures.network import networks_service  # NOQA: F401
from fixtures.network import ovirtmgmt_network  # NOQA: F401

from fixtures.host import hosts_service  # NOQA: F401
from fixtures.host import host_0  # NOQA: F401
from fixtures.host import host_1  # NOQA: F401

from fixtures.engine import system_service  # NOQA: F401
from fixtures.engine import engine  # NOQA: F401
from fixtures.engine import api  # NOQA: F401

from fixtures.storage import storage_domains_service  # NOQA: F401
from fixtures.storage import default_storage_domain  # NOQA: F401
from fixtures.storage import disks_service  # NOQA: F401

from fixtures.data_center import data_centers_service  # NOQA: F401
from fixtures.data_center import default_data_center  # NOQA: F401

from fixtures.virt import vms_service  # NOQA: F401


def pytest_addoption(parser):
    parser.addoption('--lago-env', action='store')


@pytest.fixture(scope='session')
def env():
    workdir = pytest.config.getoption('--lago-env')
    lago_env = lagosdk.load_env(workdir=workdir)

    lago_env.start()

    # TODO: once a proper solution for repo server w/o OST lago plugin
    # is available, remove this hack and use it instead.
    try:
        repo_server = create_repo_server(workdir, lago_env)
        yield lago_env
    finally:
        repo_server.shutdown()
        lago_env.destroy()
