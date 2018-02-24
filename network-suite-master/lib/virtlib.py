#
# Copyright 2017-2018 Red Hat, Inc.
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
import time

from contextlib import contextmanager

import ovirtsdk4
from ovirtsdk4 import types

from lib import netlib
from lib import clusterlib
from lib import syncutil
from lib.sdkentity import SDKRootEntity
from lib.sdkentity import SDKSubEntity


@contextmanager
def vm_pool(system, size):
    pool = [Vm(system) for _ in range(size)]
    try:
        yield pool
    finally:
        for vm in pool[::-1]:
            if vm.service is None:
                continue
            vm.remove()


class SnapshotStatus(object):

    IN_PREVIEW = types.SnapshotStatus.IN_PREVIEW
    NOT_READY = types.SnapshotStatus.LOCKED
    READY = types.SnapshotStatus.OK


class SnapshotNotInPreviewError(Exception):
    pass


class Vm(SDKRootEntity):

    @property
    def host(self):
        return self.get_sdk_type().host

    @property
    def status(self):
        return self.get_sdk_type().status

    def run(self):
        self._service.start()

    def stop(self):
        VM_IS_NOT_RUNNING = 'VM is not running'

        try:
            self._service.stop()
        except ovirtsdk4.Error as e:
            if VM_IS_NOT_RUNNING in e.message:
                return
            raise

    def snapshots(self, snapshot_id=None):
        snapshots = []
        for ss in self._service.snapshots_service().list():
            if snapshot_id is None or snapshot_id == ss.id:
                snapshot = VmSnapshot(self)
                snapshot.import_by_id(ss.id)
                snapshots.append(snapshot)
        return snapshots

    def migrate(self, dst_host_name):
        self._service.migrate(host=types.Host(name=dst_host_name))

    def get_vnic(self, vnic_name):
        vnic = netlib.Vnic(self)
        vnic.import_by_name(vnic_name)
        return vnic

    def attach_disk(self, disk, interface=types.DiskInterface.VIRTIO,
                    bootable=True, active=True):
        params = types.DiskAttachment(
            disk=disk.get_sdk_type(),
            interface=interface,
            bootable=bootable,
            active=active
        )
        disk_attachments_service = self._service.disk_attachments_service()
        disk_attachment = disk_attachments_service.add(params)
        return disk_attachment.id

    def remove(self):
        with self.wait_for_down_status():
            self.stop()
        try:
            self._avoid_unknown_dc_status_bz_1532578()
            super(Vm, self).remove()
        except self._unspecific_sdk_error_bz_1533016():
            self._retry_removal_due_to_locked_status_bz_1530315()

    def _avoid_unknown_dc_status_bz_1532578(self):
        self._get_data_center().wait_for_up_status()

    def _unspecific_sdk_error_bz_1533016(self):
        return ovirtsdk4.Error

    def _retry_removal_due_to_locked_status_bz_1530315(self):
        time.sleep(30)
        try:
            self._avoid_unknown_dc_status_bz_1532578()
            super(Vm, self).remove()
        except ovirtsdk4.NotFoundError:
            pass

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

    def create(self, vm_name, cluster, template, stateless=False):
        """
        :type vm_name: string
        :type cluster: clusterlib.Cluster
        :type template: string
        :type stateless: boolean
        """

        sdk_type = types.Vm(
            name=vm_name,
            cluster=cluster.get_sdk_type(),
            template=types.Template(name=template),
            stateless=stateless
            )
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, system):
        return system.vms_service

    def _wait_for_status(self, status):
        syncutil.sync(exec_func=lambda: self.status,
                      exec_func_args=(),
                      success_criteria=lambda s: s == status)

    def _sync_disk_attachment(self, disk_attachment_id):
        syncutil.sync(
            exec_func=self._is_disk_attachment_active,
            exec_func_args=(disk_attachment_id,),
            success_criteria=lambda s: s
        )

    def _is_disk_attachment_active(self, disk_attachment_id):
        disk_attachments_service = self._service.disk_attachments_service()
        disk_attachment_service = disk_attachments_service.attachment_service(
            disk_attachment_id)
        return disk_attachment_service.get().active

    def _get_data_center(self):
        cluster = clusterlib.Cluster(self._parent_sdk_system)
        cluster.import_by_id(self.get_sdk_type().cluster.id)
        return cluster.get_data_center()


class VmSnapshot(SDKSubEntity):

    def _get_parent_service(self, vm):
        return vm.service.snapshots_service()

    def create(self, description, persist_memorystate=False):
        sdk_type = types.Snapshot(
            persist_memorystate=persist_memorystate,
            description=description
        )
        self._create_sdk_entity(sdk_type)

    def commit(self):
        if self.get_sdk_type().snapshot_status != SnapshotStatus.IN_PREVIEW:
            raise SnapshotNotInPreviewError
        self._parent_sdk_entity.commit_snapshot()

    def preview(self):
        self._parent_sdk_entity.service.preview_snapshot(
            snapshot=self.get_sdk_type().id
        )

    def restore(self):
        if self.get_sdk_type().snapshot_status == SnapshotStatus.IN_PREVIEW:
            self._parent_sdk_entity.commit_snapshot()
        else:
            self._service.restore(
                restore_memory=self.get_sdk_type().persist_memorystate
            )

    def wait_for_ready_status(self):
        syncutil.sync(
            exec_func=lambda: self.get_sdk_type().snapshot_status,
            exec_func_args=(),
            success_criteria=lambda status: status == SnapshotStatus.READY
        )

    def wait_for_snapshot_removal(self, snapshot_id):
        syncutil.sync(
            exec_func=self._is_snapshot_present,
            exec_func_args=(),
            success_criteria=lambda present: not present
        )

    def _is_snapshot_present(self):
        try:
            self.get_sdk_type()
        except ovirtsdk4.NotFoundError:
            return False
        return True
