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
from contextlib import contextmanager

from ovirtsdk4 import types

from lib import syncutil
from lib.sdkentity import SDKEntity


TEMPLATE_BLANK = 'Blank'


class Vm(SDKEntity):

    @property
    def host(self):
        return self.sdk_type.host

    @property
    def status(self):
        return self.sdk_type.status

    def run(self):
        self._service.start()

    def stop(self):
        self._service.stop()

    def migrate(self, dst_host_name):
        self._service.migrate(host=types.Host(name=dst_host_name))

    def attach_disk(self, disk, interface=types.DiskInterface.VIRTIO,
                    bootable=True, active=True):
        params = types.DiskAttachment(
            disk=disk.sdk_type,
            interface=interface,
            bootable=bootable,
            active=active
        )
        disk_attachments_service = self._service.disk_attachments_service()
        disk_attachment = disk_attachments_service.add(params)
        return disk_attachment.id

    @contextmanager
    def wait_for_disk_up_status(self, disk, disk_attachment_id):
        yield
        disk.wait_for_up_status()
        self._sync_disk_attachment(disk_attachment_id)

    @contextmanager
    def wait_for_up_status(self):
        yield
        self._wait_for_status(types.VmStatus.UP)

    @contextmanager
    def wait_for_down_status(self):
        yield
        self._wait_for_status(types.VmStatus.DOWN)

    def _build_sdk_type(self, vm_name, cluster, template):
        return types.Vm(
            name=vm_name,
            cluster=types.Cluster(name=cluster),
            template=types.Template(name=template)
        )

    def _wait_for_status(self, status):
        syncutil.sync(exec_func=lambda: self.status,
                      exec_func_args=(),
                      success_criteria=lambda s: s == status)

    def _sync_disk_attachment(self, disk_attachment_id):
        syncutil.sync(
            exec_func=lambda: self._is_disk_attachment_active(
                disk_attachment_id),
            exec_func_args=(),
            success_criteria=lambda s: s is True
        )

    def _is_disk_attachment_active(self, disk_attachment_id):
        disk_attachments_service = self._service.disk_attachments_service()
        disk_attachment_service = disk_attachments_service.attachment_service(
            disk_attachment_id)
        return disk_attachment_service.get().active
