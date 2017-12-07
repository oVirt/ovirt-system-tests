#
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
from ovirtsdk4 import types

from lib import syncutil
from lib.sdkentity import SDKEntity


MiB = 2 ** 20
GiB = 2 ** 30


class Disk(SDKEntity):

    @property
    def status(self):
        return self.sdk_type.status

    def _build_sdk_type(self, disk_name, sd_name, provisioned_size=2 * GiB,
                        disk_format=types.DiskFormat.COW, status=None,
                        sparse=True):
        return types.Disk(
            name=disk_name,
            provisioned_size=provisioned_size,
            format=disk_format,
            storage_domains=[types.StorageDomain(name=sd_name)],
            status=status,
            sparse=sparse
        )

    def wait_for_up_status(self):
        syncutil.sync(exec_func=lambda: self.status,
                      exec_func_args=(),
                      success_criteria=lambda s: s == types.DiskStatus.OK)
