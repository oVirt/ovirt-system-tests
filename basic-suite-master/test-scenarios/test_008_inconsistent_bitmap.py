#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#
"""
End-to-end test for the inconsistent-bitmap-auto-removal fix on live disk extend.

Scenario:
  1. Create a non-HA VM with a 1 GB qcow2 incremental-backup disk on NFS.
  2. Run a full backup to create a persistent checkpoint + dirty bitmap.
  3. SIGKILL the qemu process on the host, leaving the bitmap IN_USE in qcow2.
  4. Start the VM -- qemu now marks the bitmap inconsistent in memory.
  5. Live-extend the disk to 2 GB. The vdsm fix detects and removes the
     inconsistent bitmaps before calling block_resize; the engine emits
     audit event 384 (VM_DISK_INCONSISTENT_BITMAPS_REMOVED) plus the normal
     extend success event 371.
  6. Tolerant cleanup of the now-stale checkpoints, then remove the VM.

Event 384 is the discriminator: if the bitmap never became inconsistent,
or the fix never ran, no audit event is logged and the test fails loudly.
"""

import logging

import pytest

from ovirtsdk4 import types

from ost_utils import assert_utils
from ost_utils import constants
from ost_utils import engine_utils
from ost_utils.pytest import order_by
from ost_utils.pytest.fixtures.vm import *  # noqa: F401,F403
from ost_utils.storage_utils import backup
from ost_utils import test_utils

LOGGER = logging.getLogger(__name__)

MB = 2**20
GB = 2**30

BITMAP_VM_NAME = "inconsistent_bitmap_vm"
BITMAP_DISK_NAME = "inconsistent_bitmap_disk"
BITMAP_DISK_INITIAL_SIZE = 1 * GB
BITMAP_DISK_EXTENDED_SIZE = 2 * GB

# Audit log event ids (see AuditLogType.java)
USER_EXTEND_DISK_SIZE_SUCCESS = 371
VM_DISK_INCONSISTENT_BITMAPS_REMOVED = 384


_TEST_LIST = [
    "test_add_bitmap_vm",
    "test_add_bitmap_disk",
    "test_run_bitmap_vm",
    "test_backup_bitmap_vm",
    "test_kill_qemu",
    "test_restart_bitmap_vm",
    "test_live_extend_with_inconsistent_bitmap",
    "test_cleanup_bitmap_checkpoints",
    "test_remove_bitmap_vm",
]


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def ansible_host_for_bitmap_vm(get_ansible_host_for_vm):
    return get_ansible_host_for_vm(BITMAP_VM_NAME)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _disk_attachment(vm_name, disk_name, sd_name, size, incremental=True):
    disk = types.Disk(
        storage_domains=[types.StorageDomain(name=sd_name)],
        name=disk_name,
        provisioned_size=size,
        format=types.DiskFormat.COW,
        sparse=True,
        active=True,
        bootable=True,
        backup=types.DiskBackup.INCREMENTAL if incremental else None,
    )
    return types.DiskAttachment(disk=disk, interface=types.DiskInterface.VIRTIO)


def _qemu_pid_for_bitmap_vm(ansible_host):
    res = ansible_host.shell(f"pgrep -f 'qemu.*guest={BITMAP_VM_NAME}'")
    return int(res["stdout"].strip().splitlines()[0])


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


@order_by(_TEST_LIST)
def test_add_bitmap_vm(engine_api, ost_cluster_name):
    engine = engine_api.system_service()
    engine.vms_service().add(
        types.Vm(
            name=BITMAP_VM_NAME,
            description="VM for inconsistent-bitmap live-extend test",
            memory=512 * MB,
            cluster=types.Cluster(name=ost_cluster_name),
            template=types.Template(name="Blank"),
            high_availability=types.HighAvailability(enabled=False),
        )
    )
    vm_service = test_utils.get_vm_service(engine, BITMAP_VM_NAME)
    assert assert_utils.equals_within_short(
        lambda: vm_service.get().status, types.VmStatus.DOWN
    )


@order_by(_TEST_LIST)
def test_add_bitmap_disk(engine_api):
    engine = engine_api.system_service()
    disk_attachments_service = test_utils.get_disk_attachments_service(
        engine, BITMAP_VM_NAME
    )
    assert disk_attachments_service.add(
        _disk_attachment(
            BITMAP_VM_NAME,
            BITMAP_DISK_NAME,
            constants.SD_NFS_NAME,
            BITMAP_DISK_INITIAL_SIZE,
        )
    )
    disk_service = test_utils.get_disk_service(engine, BITMAP_DISK_NAME)
    assert assert_utils.equals_within_short(
        lambda: disk_service.get().status, types.DiskStatus.OK
    )


@order_by(_TEST_LIST)
def test_run_bitmap_vm(engine_api):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, BITMAP_VM_NAME)
    vm_service.start()
    assert assert_utils.equals_within_long(
        lambda: vm_service.get().status, types.VmStatus.UP
    )


@order_by(_TEST_LIST)
def test_backup_bitmap_vm(engine_api):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, BITMAP_VM_NAME)
    backups_service = vm_service.backups_service()
    backup.perform_incremental_vm_backup(
        engine_api, backups_service, BITMAP_DISK_NAME, "bitmap_full_backup"
    )
    checkpoints_service = vm_service.checkpoints_service()
    assert assert_utils.true_within_long(lambda: len(checkpoints_service.list()) >= 1)


@order_by(_TEST_LIST)
def test_kill_qemu(engine_api, ansible_host_for_bitmap_vm):
    """SIGKILL qemu so the bitmap stays IN_USE in the qcow2 metadata."""
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, BITMAP_VM_NAME)
    assert vm_service.get().host is not None, "VM must be running on a host before kill"

    pid = _qemu_pid_for_bitmap_vm(ansible_host_for_bitmap_vm)
    LOGGER.info("Sending SIGKILL to qemu pid=%s for vm=%s", pid, BITMAP_VM_NAME)
    ansible_host_for_bitmap_vm.shell(f"/usr/bin/kill -s SIGKILL {pid}")

    # Non-HA VM should stay DOWN after crash.
    assert assert_utils.equals_within_long(
        lambda: vm_service.get().status, types.VmStatus.DOWN
    )


@order_by(_TEST_LIST)
def test_restart_bitmap_vm(engine_api):
    """Starting qemu on a volume with IN_USE bitmaps marks them inconsistent."""
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, BITMAP_VM_NAME)
    vm_service.start()
    assert assert_utils.equals_within_long(
        lambda: vm_service.get().status, types.VmStatus.UP
    )


@order_by(_TEST_LIST)
def test_live_extend_with_inconsistent_bitmap(engine_api):
    """The actual fix assertion.

    Without the fix this extend would fail (qemu refuses block_resize on
    a drive with inconsistent bitmaps). With the fix, vdsm removes the
    bitmaps first and surfaces them via audit event 384.
    """
    engine = engine_api.system_service()
    disk_attachments_service = test_utils.get_disk_attachments_service(
        engine, BITMAP_VM_NAME
    )

    for attachment in disk_attachments_service.list():
        if test_utils.get_disk_service(engine, BITMAP_DISK_NAME).get().id == (
            engine_api.follow_link(attachment.disk).id
        ):
            attachment_service = disk_attachments_service.attachment_service(
                attachment.id
            )
            with engine_utils.wait_for_event(
                engine,
                [USER_EXTEND_DISK_SIZE_SUCCESS, VM_DISK_INCONSISTENT_BITMAPS_REMOVED],
            ):
                attachment_service.update(
                    types.DiskAttachment(
                        disk=types.Disk(provisioned_size=BITMAP_DISK_EXTENDED_SIZE)
                    )
                )

    disk_service = test_utils.get_disk_service(engine, BITMAP_DISK_NAME)
    assert assert_utils.equals_within_short(
        lambda: disk_service.get().status, types.DiskStatus.OK
    )
    assert assert_utils.equals_within_short(
        lambda: disk_service.get().provisioned_size, BITMAP_DISK_EXTENDED_SIZE
    )


@order_by(_TEST_LIST)
def test_cleanup_bitmap_checkpoints(engine_api):
    """Engine-side checkpoints now point at bitmaps that vdsm has already
    removed. Removal may fail or succeed depending on engine version;
    tolerate either outcome -- the cleanup is best-effort."""
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, BITMAP_VM_NAME)
    checkpoints_service = vm_service.checkpoints_service()

    for ckpt in list(checkpoints_service.list()):
        try:
            checkpoints_service.checkpoint_service(id=ckpt.id).remove()
        except Exception as exc:  # noqa: BLE001 -- best-effort cleanup
            LOGGER.warning("checkpoint %s removal failed (expected): %s", ckpt.id, exc)


@order_by(_TEST_LIST)
def test_remove_bitmap_vm(engine_api):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, BITMAP_VM_NAME)
    if vm_service.get().status == types.VmStatus.UP:
        vm_service.stop()
        assert assert_utils.equals_within_long(
            lambda: vm_service.get().status, types.VmStatus.DOWN
        )
    vm_service.remove(force=True)
