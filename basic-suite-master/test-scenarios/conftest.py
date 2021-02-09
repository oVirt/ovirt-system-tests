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

import os

from ost_utils.pytest import pytest_collection_modifyitems

from ost_utils.pytest.fixtures.ansible import ansible_clean_private_dirs
from ost_utils.pytest.fixtures.ansible import ansible_collect_logs

from ost_utils.pytest.fixtures.artifacts import artifacts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.artifacts import collect_artifacts

from ost_utils.pytest.fixtures.backend import backend
from ost_utils.pytest.fixtures.backend import hosts_hostnames

from ost_utils.pytest.fixtures.defaults import hostnames_to_add
from ost_utils.pytest.fixtures.defaults import hostnames_to_reboot

from ost_utils.pytest.running_time import *


if os.environ.get("USE_LAGO_OST_PLUGIN", "0") == "1":
    import ovirtlago
    import ovirtlago.prefix
    import pytest
    from ovirtlago import testlib

    @pytest.fixture(scope="session")
    def prefix():
        yield testlib.get_test_prefix()

    @pytest.fixture(autouse=True, scope="session")
    def repo_server(prefix):
        with ovirtlago.server.repo_server_context(
            gw_ip=prefix.virt_env.get_net().gw(),
            port=ovirtlago.constants.REPO_SERVER_PORT,
            root_dir=prefix.paths.internal_repo()
        ):
            yield
