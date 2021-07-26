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

from ost_utils import coverage
from ost_utils import utils
from ost_utils import shell


@pytest.fixture(scope="session")
def artifacts_dir():
    return os.path.join(os.environ["OST_REPO_ROOT"], "exported-artifacts")


@pytest.fixture(scope="session")
def artifact_list():
    return [
        '/etc/dnf',
        '/etc/firewalld',
        '/etc/httpd/conf',
        '/etc/httpd/conf.d',
        '/etc/httpd/conf.modules.d',
        '/etc/ovirt-engine',
        '/etc/ovirt-engine-dwh',
        '/etc/ovirt-engine-metrics',
        '/etc/ovirt-engine-setup.conf.d',
        '/etc/ovirt-engine-setup.env.d',
        '/etc/ovirt-host-deploy.conf.d',
        '/etc/ovirt-imageio-proxy',
        '/etc/ovirt-provider-ovn',
        '/etc/ovirt-vmconsole',
        '/etc/ovirt-web-ui',
        '/etc/resolv.conf',
        '/etc/sysconfig',
        '/etc/yum',
        '/etc/yum.repos.d',
        '/tmp/dnf_yum.conf',
        '/var/cache/ovirt-engine',
        '/var/lib/ovirt-engine/setup/answers',
        '/var/lib/pgsql/upgrade_rh-postgresql95-postgresql.log',
        '/var/log',
    ]


@pytest.fixture(scope="session")
def artifacts(all_hostnames, artifact_list):
    return {hostname: artifact_list for hostname in all_hostnames}


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


@pytest.fixture(scope="session", autouse=True)
def collect_vdsm_coverage_artifacts(artifacts_dir, ansible_host0,
                                    ansible_hosts):
    yield
    if os.environ.get("coverage", "false") == "true":
        output_path = os.path.join(artifacts_dir, "coverage/")
        os.makedirs(output_path, exist_ok=True)
        coverage.vdsm.collect(ansible_host0, ansible_hosts, output_path)
