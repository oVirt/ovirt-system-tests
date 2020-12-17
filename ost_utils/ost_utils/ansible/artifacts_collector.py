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

import yaml

from ost_utils import shell
from ost_utils.ansible import module_mapper as mm


SUITE_PATH = os.environ.get('SUITE')
_ENGINE = 'engine'
_HOST0 = 'host-0'
_HOST1 = 'host-1'
_LAGO_ENGINE_PATTERN = '~lago-.*-' + _ENGINE
_LAGO_HOST0_PATTERN = '~lago-.*-' + _HOST0
_LAGO_HOST1_PATTERN = '~lago-.*-' + _HOST1


class ArtifactsCollector(object):

    def __init__(self, host_pattern, host_key, artifacts_target_dir):
        self._module_mapper = mm.module_mapper_for(host_pattern)
        self.host_key = host_key
        self.artifacts_target_dir = artifacts_target_dir
        self.domain_name = None

    def _retrieve_artifacts_list(self):
        """
        :return: [] list of files to collect on this machine
        """
        with open(os.path.join(SUITE_PATH, 'LagoInitFile'), "r") as file:
            yaml_dict = yaml.safe_load(file)
            domains_dict = yaml_dict['domains']

            self.domain_name = ''.join(
                [key for key in domains_dict.keys() if self.host_key in key]
            )
        return domains_dict[self.domain_name]['artifacts']

    def collect(self):
        artifacts_list_string = ','.join(self._retrieve_artifacts_list())
        archive_name = "artifacts.tar.gz"
        local_archive_dir = os.path.join(
            self.artifacts_target_dir, "test_logs", self.domain_name)
        local_archive_path = os.path.join(local_archive_dir, archive_name)
        remote_archive_path = os.path.join("/tmp", archive_name)
        os.makedirs(local_archive_dir, exist_ok=True)

        self._module_mapper.archive(
            path=artifacts_list_string, dest=remote_archive_path
        )
        self._module_mapper.fetch(
            src=remote_archive_path, dest=local_archive_path, flat='yes'
        )
        shell.shell(
            ["tar", "-xf", local_archive_path, "-C", local_archive_dir]
        )
        shell.shell(["rm", local_archive_path])


class EngineArtifactsCollector(ArtifactsCollector):
    def __init__(self, artifacts_dir):
        super(EngineArtifactsCollector, self).__init__(
            _LAGO_ENGINE_PATTERN, _ENGINE, artifacts_dir)


class Host0ArtifactsCollector(ArtifactsCollector):
    def __init__(self, artifacts_dir):
        super(Host0ArtifactsCollector, self).__init__(
            _LAGO_HOST0_PATTERN, _HOST0, artifacts_dir)


class Host1ArtifactsCollector(ArtifactsCollector):
    def __init__(self, artifacts_dir):
        super(Host1ArtifactsCollector, self).__init__(
            _LAGO_HOST1_PATTERN, _HOST1, artifacts_dir)
