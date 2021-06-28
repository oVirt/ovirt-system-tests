#
# Copyright 2017-2021 Red Hat, Inc.
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

import ovirtsdk4 as sdk4
import ovirtsdk4.types as types

from ost_utils import assertions


def perform_vm_backup(
        vm_backup_service, disks_service, disk,
        from_checkpoint_id=None, correlation_id=None):
    backup = vm_backup_service.add(
        types.Backup(
            disks=[types.Disk(id=disk.id)],
            from_checkpoint_id=from_checkpoint_id
        ), query={'correlation_id': correlation_id}
    )

    backup_service = vm_backup_service.backup_service(backup.id)
    assertions.assert_true_within_long(
        lambda: backup_service.get().phase == types.BackupPhase.READY,
        allowed_exceptions=[sdk4.NotFoundError]
    )

    backup = backup_service.get()
    created_checkpoint_id = backup.to_checkpoint_id

    backup_service.finalize()

    assertions.assert_true_within_long(
        lambda: backup_service.get().phase == types.BackupPhase.SUCCEEDED
    )
    assertions.assert_true_within_long(
        lambda:
        disks_service.disk_service(disk.id).get().status == types.DiskStatus.OK
    )

    return created_checkpoint_id


def perform_incremental_vm_backup(engine_api, backups_service, disk_name, correlation_id):
    engine = engine_api.system_service()
    disks_service = engine.disks_service()
    disk = disks_service.list(search='name={}'.format(disk_name))[0]

    # Start a full backup
    full_checkpoint_id = perform_vm_backup(
        backups_service,
        disks_service, disk,
        correlation_id="full_" + correlation_id)

    # Start an incremental backup using the checkpoint created before
    perform_vm_backup(
        backups_service,
        disks_service, disk,
        from_checkpoint_id=full_checkpoint_id,
        correlation_id="incremental_" + correlation_id)


def remove_vm_root_checkpoint(checkpoints_service):
    vm_checkpoints = checkpoints_service.list()
    root_checkpoint = vm_checkpoints[0]
    checkpoint_service = checkpoints_service.checkpoint_service(id=root_checkpoint.id)
    checkpoint_service.remove()

    assertions.assert_true_within_short(
        lambda: len(checkpoints_service.list()) == len(vm_checkpoints) - 1
    )
