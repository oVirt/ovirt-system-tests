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

from ost_utils import shell
from ost_utils.ansible import module_mappers as mm


def collect(hostname, artifacts_list, target_dir):
    artifacts_list_string = ','.join(artifacts_list)
    module_mapper = mm.module_mapper_for(hostname)
    archive_name = "artifacts.tar.gz"
    local_archive_dir = os.path.join(target_dir, "test_logs", hostname)
    local_archive_path = os.path.join(local_archive_dir, archive_name)
    remote_archive_path = os.path.join("/tmp", archive_name)
    os.makedirs(local_archive_dir, exist_ok=True)
    module_mapper.archive(path=artifacts_list_string, dest=remote_archive_path)
    module_mapper.fetch(
        src=remote_archive_path, dest=local_archive_path, flat='yes'
    )
    shell.shell(
        ["tar", "-xf", local_archive_path, "-C", local_archive_dir]
    )
    shell.shell(["rm", local_archive_path])
