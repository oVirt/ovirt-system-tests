#
# Copyright 2020-2021 Red Hat, Inc.
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

import functools
import os

import pytest

from ost_utils import utils
from ost_utils import shell


@pytest.fixture(scope="session")
def artifacts_dir():
    return os.path.join(os.environ["OST_REPO_ROOT"], "exported-artifacts")


@pytest.fixture(scope="session")
def artifacts(backend, all_hostnames, artifact_list):
    try:
        artifacts = backend.artifacts()
    except KeyError:
        artifacts = {hostname: artifact_list for hostname in all_hostnames}
    return artifacts


@pytest.fixture(scope="session", autouse=True)
def collect_artifacts(artifacts_dir, artifacts, ansible_by_hostname):
    def collect(hostname, artifacts_list, target_dir):
        artifacts_list_string = ','.join(artifacts_list)
        ansible_handle = ansible_by_hostname(hostname)
        archive_name = "artifacts.tar.gz"
        local_archive_dir = os.path.join(target_dir, "test_logs", hostname)
        local_archive_path = os.path.join(local_archive_dir, archive_name)
        remote_archive_path = os.path.join("/tmp", archive_name)
        os.makedirs(local_archive_dir, exist_ok=True)
        ansible_handle.archive(path=artifacts_list_string, dest=remote_archive_path)
        ansible_handle.fetch(
            src=remote_archive_path, dest=local_archive_path, flat='yes'
        )
        shell.shell(
            ["tar", "-xf", local_archive_path, "-C", local_archive_dir]
        )
        shell.shell(["rm", local_archive_path])

    yield
    calls = [
        functools.partial(collect, hostname, artifact_list, artifacts_dir)
        for hostname, artifact_list in artifacts.items()
    ]
    utils.invoke_different_funcs_in_parallel(*calls)
