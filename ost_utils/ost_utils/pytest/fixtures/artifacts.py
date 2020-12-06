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

import pytest

from ost_utils import ansible
from ost_utils import utils


@pytest.fixture(scope="session")
def artifacts_dir():
    return os.path.join(os.environ["OST_REPO_ROOT"], "exported-artifacts")


@pytest.fixture(scope="session", autouse=True)
def collect_artifacts(artifacts_dir):
    yield
    utils.invoke_different_funcs_in_parallel(
        ansible.EngineArtifactsCollector(artifacts_dir).collect,
        ansible.Host0ArtifactsCollector(artifacts_dir).collect,
        ansible.Host1ArtifactsCollector(artifacts_dir).collect
    )
