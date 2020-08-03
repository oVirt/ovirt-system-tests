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

import os

import ovirtlago
import ovirtlago.prefix
import pytest

from ovirtlago import testlib


@pytest.fixture(scope="session")
def root_password():
    # TODO: read it properly
    return "123456"


@pytest.fixture(scope="session")
def prefix():
    yield testlib.get_test_prefix()


@pytest.fixture(scope="session")
def api_v4(prefix):
    yield prefix.virt_env.engine_vm().get_api(api_ver=4)


@pytest.fixture(autouse=True, scope="session")
def repo_server(prefix):
    with ovirtlago.server.repo_server_context(
        gw_ip=prefix.virt_env.get_net().gw(),
        port=ovirtlago.constants.REPO_SERVER_PORT,
        root_dir=prefix.paths.internal_repo()
    ):
        yield
