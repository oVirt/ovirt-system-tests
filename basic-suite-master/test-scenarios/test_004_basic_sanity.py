#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#
from __future__ import absolute_import

import functools
import logging
import os
from os import EX_OK
import pty
import re
import subprocess
from time import sleep
import uuid

import ovirtsdk4
import ovirtsdk4.types as types

import pytest

from ost_utils import ansible
from ost_utils import assert_utils
from ost_utils import constants
from ost_utils import engine_utils
from ost_utils import host_utils
from ost_utils.shell import shell
from ost_utils import ssh
from ost_utils import test_utils
from ost_utils import utils
from ost_utils import versioning
from ost_utils.pytest import order_by
from ost_utils.pytest.fixtures.backend import tested_ip_version
from ost_utils.pytest.fixtures.network import management_subnet
from ost_utils.pytest.fixtures.sdk import *
from ost_utils.pytest.fixtures.virt import *
from ost_utils.pytest.fixtures.vm import *

from ost_utils.storage_utils import backup

LOGGER = logging.getLogger(__name__)


KB = 2 ** 10
MB = 2 ** 20
GB = 2 ** 30

TEMPLATE_CENTOS7 = 'centos7_template'
TEMPLATE_BLANK = 'Blank'

SD_NFS_NAME = 'nfs'
SD_SECOND_NFS_NAME = 'second-nfs'
SD_ISCSI_NAME = 'iscsi'

VM_USER_NAME = 'cirros'
VM_PASSWORD = 'gocubsgo'

VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
VM2_NAME = 'vm2'
VM_TO_CLONE_NAME = 'vm_to_clone'
BACKUP_VM_NAME = 'backup_vm'
CLONED_VM_NAME = 'cloned_vm'
IMPORTED_VM_NAME = 'imported_vm'
IMPORTED_TEMP_NAME = 'imported_temp'
OVF_VM_NAME = 'ovf_vm'
VMPOOL_NAME = 'test-pool'
DISK0_NAME = '%s_disk0' % VM0_NAME
DISK1_NAME = '%s_disk1' % VM1_NAME
DISK2_NAME = '%s_disk2' % VM2_NAME
DISK3_NAME = '%s_disk3' % VM1_NAME
FLOATING_DISK_NAME = 'floating_disk'
BACKUP_DISK_NAME = '%s_disk' % BACKUP_VM_NAME

SD_TEMPLATES_NAME = 'templates'

VM_NETWORK = u'VM Network with a very long name and עברית'

SNAPSHOT_DESC_1 = 'dead_snap1'
SNAPSHOT_DESC_2 = 'dead_snap2'
SNAPSHOT_FOR_BACKUP_VM = 'backup_snapshot'
SNAPSHOT_DESC_MEM = 'memory_snap'
SNAPSHOT_DESC_OFF = 'offline_snap'

VDSM_LOG = '/var/log/vdsm/vdsm.log'

OVA_VM_EXPORT_NAME = 'ova_vm.ova'
OVA_TEMP_EXPORT_NAME = 'ova_temp.ova'
OVA_DIR = '/var/tmp'
IMPORTED_OVA_NAME = 'ova:///var/tmp/ova_vm.ova'
IMPORTED_TEMP_OVA_NAME = 'ova:///var/tmp/ova_temp.ova'
OVA_FILE_LOCATION = '%s/%s' % (OVA_DIR, OVA_VM_EXPORT_NAME)

_TEST_LIST = [
    "test_verify_add_all_hosts",
    "test_reconstruct_master_domain",
    "test_add_vm1_from_template",
    "test_verify_add_vm1_from_template",
    "test_add_disks",
    "test_copy_template_disk",
    "test_add_floating_disk",
    "test_add_snapshot_for_backup",
    "test_clone_powered_off_vm",
    "test_verify_template_disk_copied_and_removed",
    "test_cold_incremental_backup_vm2",
    "test_run_vms",
    "test_attach_snapshot_to_backup_vm",
    "test_verify_transient_folder",
    "test_verify_and_remove_cloned_vm",
    "test_remove_backup_vm_and_backup_snapshot",
    "test_vm0_is_alive",
    "test_hotplug_memory",
    "test_suspend_resume_vm0",
    "test_verify_backup_snapshot_removed",
    "test_export_vm2",
    "test_verify_vm2_run",
    "test_extend_disk1",
    "test_sparsify_disk1",
    "test_template_export",
    "test_template_update",
    "test_verify_vm2_exported",
    "test_live_incremental_backup_vm2",
    "test_remove_vm2_backup_checkpoints",
    "test_import_vm_preallocated",
    "test_ha_recovery",
    "test_check_coredump_generated",
    "test_verify_suspend_resume_vm0",
    "test_verify_vm_import_preallocated",
    "test_verify_template_exported",
    "test_hotunplug_memory",
    "test_hotplug_disk",
    "test_hotplug_nic",
    "test_hotplug_cpu",
    "test_next_run_unplug_cpu",
    "test_disk_operations",
    "test_offline_snapshot_restore",
    "test_import_template",
    "test_live_storage_migration",
    "test_verify_offline_snapshot_restore",
    "test_remove_vm2_lease",
    "test_hotunplug_disk",
    "test_make_snapshot_with_memory",
    "test_add_vm_pool",
    "test_ovf_import",
    "test_verify_template_import",
    "test_preview_snapshot_with_memory",
    "test_verify_ovf_import",
    "test_update_template_version",
    "test_check_snapshot_with_memory",
    "test_vmconsole",
    "test_verify_update_template_version",
    "test_update_vm_pool",
    "test_remove_vm_pool",
    "test_vdsm_recovery",
]


@pytest.fixture(scope="session")
def vm_user():
    return VM_USER_NAME


@pytest.fixture(scope="session")
def vm_password():
    return VM_PASSWORD


@pytest.fixture(scope="session")
def vm_ssh(get_vm_ip, vm_user, vm_password):
    def run_ssh(vm_name_or_ip, command):
        if isinstance(command, str):
            command = command.split()
        return ssh.ssh(
            ip_addr=get_vm_ip(vm_name_or_ip),
            command=command,
            username=vm_user,
            password=vm_password,
        )

    return run_ssh


@order_by(_TEST_LIST)
def test_verify_add_all_hosts(hosts_service, ost_dc_name):
    assert assert_utils.true_within(
        lambda: host_utils.all_hosts_up(hosts_service, ost_dc_name),
        timeout=constants.ADD_HOST_TIMEOUT,
    )


def _verify_vm_state(engine, vm_name, state):
    vm_service = test_utils.get_vm_service(engine, vm_name)
    assert assert_utils.equals_within_long(lambda: vm_service.get().status, state)
    return vm_service


def _verify_vm_disks_state(vm_name, state, get_disk_services_for_vm_or_template, get_vm_service_for_vm):
    vm_service = get_vm_service_for_vm(vm_name)
    disks_service = get_disk_services_for_vm_or_template(vm_service)

    for disk_service in disks_service:
        assert assert_utils.equals_within_short(lambda: disk_service.get().status, state)


@pytest.fixture(scope="session")
def assert_vm_is_alive(ansible_host0, vm_ssh, tested_ip_version):
    def is_alive(vm_name):
        def _ping():
            ansible_host0.shell(f'ping -{tested_ip_version} -c 1 -W 60 {vm_name}')
            return True

        assert assert_utils.true_within_long(_ping, allowed_exceptions=[ansible.AnsibleExecutionError])

        assert vm_ssh(vm_name, 'true').code == EX_OK

    return is_alive


def _disk_attachment(**params):
    attachment_params = params.pop('attachment_params')
    disk = types.Disk(**params)
    return types.DiskAttachment(disk=disk, **attachment_params)


@order_by(_TEST_LIST)
def test_add_disks(engine_api, cirros_image_disk_name):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    cirros_disk = test_utils.get_disk_service(
        engine,
        cirros_image_disk_name,
    )
    assert vm_service and cirros_disk

    disks_params = {
        (VM0_NAME, cirros_image_disk_name): {
            'storage_domains': [types.StorageDomain(name=SD_ISCSI_NAME)],
            'id': cirros_disk.get().id,
            'attachment_params': {
                'interface': types.DiskInterface.VIRTIO,
                'active': True,
                'bootable': True,
            },
        },
        (VM1_NAME, DISK1_NAME): {
            'storage_domains': [types.StorageDomain(name=SD_NFS_NAME)],
            'name': DISK1_NAME,
            'provisioned_size': 1 * GB,
            'format': types.DiskFormat.COW,
            'sparse': True,
            'backup': types.DiskBackup.INCREMENTAL,
            'active': True,
            'bootable': True,
            'attachment_params': {
                'interface': types.DiskInterface.VIRTIO,
            },
        },
        (VM2_NAME, DISK2_NAME): {
            'storage_domains': [types.StorageDomain(name=SD_SECOND_NFS_NAME)],
            'name': DISK2_NAME,
            'provisioned_size': 1 * GB,
            'format': types.DiskFormat.COW,
            'sparse': False,
            'backup': types.DiskBackup.INCREMENTAL,
            'active': True,
            'bootable': True,
            'attachment_params': {
                'interface': types.DiskInterface.VIRTIO,
            },
        },
        (BACKUP_VM_NAME, BACKUP_DISK_NAME): {
            'storage_domains': [types.StorageDomain(name=SD_NFS_NAME)],
            'name': BACKUP_DISK_NAME,
            'provisioned_size': 1 * GB,
            'format': types.DiskFormat.COW,
            'sparse': True,
            'backup': types.DiskBackup.INCREMENTAL,
            'active': True,
            'bootable': True,
            'attachment_params': {
                'interface': types.DiskInterface.VIRTIO,
            },
        },
        (VM1_NAME, DISK3_NAME): {
            'storage_domains': [types.StorageDomain(name=SD_SECOND_NFS_NAME)],
            'name': DISK3_NAME,
            'provisioned_size': 1 * MB,
            'format': types.DiskFormat.RAW,
            'sparse': True,
            'active': True,
            'bootable': False,
            'attachment_params': {
                'interface': types.DiskInterface.VIRTIO,
            },
        },
    }

    for (vm_name, _), disk_attachment_params in disks_params.items():
        disk_attachments_service = test_utils.get_disk_attachments_service(engine, vm_name)
        assert disk_attachments_service.add(_disk_attachment(**disk_attachment_params))

    disk_services = (test_utils.get_disk_service(engine, disk_name) for _, disk_name in disks_params)
    assert assert_utils.true_within_short(
        lambda: all(disk_service.get().status == types.DiskStatus.OK for disk_service in disk_services)
    )
    # USER_ADD_DISK_TO_VM_FINISHED_SUCCESS event
    # test_utils.test_for_event(engine, 97, last_event)


@order_by(_TEST_LIST)
def test_copy_template_disk(system_service, cirros_image_disk_name):
    cirros_disk = test_utils.get_disk_service(system_service, cirros_image_disk_name)

    cirros_disk.copy(storage_domain=types.StorageDomain(name=SD_ISCSI_NAME))


@order_by(_TEST_LIST)
def test_add_floating_disk(engine_api, disks_service):
    disks_service.add(
        types.Disk(
            name=FLOATING_DISK_NAME,
            format=types.DiskFormat.COW,
            provisioned_size=2 * MB,
            active=True,
            storage_domains=[types.StorageDomain(name=SD_SECOND_NFS_NAME)],
        )
    )

    engine = engine_api.system_service()
    disk_service = test_utils.get_disk_service(engine, FLOATING_DISK_NAME)
    assert assert_utils.equals_within_short(lambda: disk_service.get().status, types.DiskStatus.OK)


@order_by(_TEST_LIST)
def test_extend_disk1(engine_api):
    engine = engine_api.system_service()
    disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM1_NAME)
    for disk_attachment in disk_attachments_service.list():
        disk = engine_api.follow_link(disk_attachment.disk)
        if disk.name == DISK1_NAME:
            attachment_service = disk_attachments_service.attachment_service(disk_attachment.id)
    with engine_utils.wait_for_event(engine, 371):  # USER_EXTEND_DISK_SIZE_SUCCESS(371)
        attachment_service.update(
            types.DiskAttachment(
                disk=types.Disk(
                    provisioned_size=2 * GB,
                )
            )
        )

        disk_service = test_utils.get_disk_service(engine, DISK1_NAME)
        assert assert_utils.equals_within_short(lambda: disk_service.get().status, types.DiskStatus.OK)
        assert assert_utils.equals_within_short(lambda: disk_service.get().provisioned_size, 2 * GB)


@order_by(_TEST_LIST)
def test_sparsify_disk1(engine_api):
    engine = engine_api.system_service()
    disk_service = test_utils.get_disk_service(engine, DISK3_NAME)
    with engine_utils.wait_for_event(engine, 1325):  # USER_SPARSIFY_IMAGE_START event
        disk_service.sparsify()

    with engine_utils.wait_for_event(engine, 1326):  # USER_SPARSIFY_IMAGE_FINISH_SUCCESS
        pass
    # Make sure disk is unlocked
    assert disk_service.get().status == types.DiskStatus.OK


@order_by(_TEST_LIST)
def test_add_snapshot_for_backup(engine_api):
    engine = engine_api.system_service()

    vm2_disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM2_NAME)
    disk = vm2_disk_attachments_service.list()[0]

    backup_snapshot_params = types.Snapshot(
        description=SNAPSHOT_FOR_BACKUP_VM,
        persist_memorystate=False,
        disk_attachments=[types.DiskAttachment(disk=types.Disk(id=disk.id))],
    )

    vm2_snapshots_service = test_utils.get_vm_snapshots_service(engine, VM2_NAME)

    correlation_id = uuid.uuid4()
    with engine_utils.wait_for_event(engine, [45, 68]):
        # USER_CREATE_SNAPSHOT(41) event
        # USER_CREATE_SNAPSHOT_FINISHED_SUCCESS(68) event
        vm2_snapshots_service.add(backup_snapshot_params, query={'correlation_id': correlation_id})

        assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))
        assert assert_utils.equals_within_long(
            lambda: vm2_snapshots_service.list()[-1].snapshot_status,
            types.SnapshotStatus.OK,
        )


@order_by(_TEST_LIST)
def test_clone_powered_off_vm(system_service, vms_service, ost_cluster_name):
    # Prepare a VM with minimal disk size to clone
    vms_service.add(
        types.Vm(
            name=VM_TO_CLONE_NAME,
            description='VM with minimal disk to clone later',
            template=types.Template(
                name=TEMPLATE_BLANK,
            ),
            cluster=types.Cluster(
                name=ost_cluster_name,
            ),
        )
    )
    vm_to_clone_service = _verify_vm_state(system_service, VM_TO_CLONE_NAME, types.VmStatus.DOWN)
    vm_to_clone_disk_attachments_service = test_utils.get_disk_attachments_service(system_service, VM_TO_CLONE_NAME)
    floating_disk_service = test_utils.get_disk_service(system_service, FLOATING_DISK_NAME)

    vm_to_clone_disk_attachments_service.add(
        types.DiskAttachment(
            disk=types.Disk(id=floating_disk_service.get().id),
            interface=types.DiskInterface.VIRTIO_SCSI,
            bootable=True,
            active=True,
        )
    )
    assert assert_utils.equals_within_short(lambda: floating_disk_service.get().status, types.DiskStatus.OK)

    correlation_id = 'clone_powered_off_vm'
    vm_to_clone_service.clone(
        vm=types.Vm(name=CLONED_VM_NAME),
        query={'correlation_id': correlation_id},
    )


@order_by(_TEST_LIST)
def test_verify_template_disk_copied_and_removed(system_service, cirros_image_disk_name):
    iscsi_sd_service = test_utils.get_storage_domain_service(system_service, SD_ISCSI_NAME)
    cirros_sd_disk_service = test_utils.get_storage_domain_disk_service_by_name(
        iscsi_sd_service, cirros_image_disk_name
    )
    assert assert_utils.equals_within_short(lambda: cirros_sd_disk_service.get().status, types.DiskStatus.OK)

    disk_id = cirros_sd_disk_service.get().id
    cirros_sd_disk_service.remove()
    assert assert_utils.true_within_short(
        lambda: disk_id not in [disk.id for disk in iscsi_sd_service.disks_service().list()]
    )


@order_by(_TEST_LIST)
def test_attach_snapshot_to_backup_vm(engine_api):
    engine = engine_api.system_service()
    vm2_snapshots_service = test_utils.get_vm_snapshots_service(engine, VM2_NAME)
    vm2_disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM2_NAME)
    vm2_disk = vm2_disk_attachments_service.list()[0]
    disk_attachments_service = test_utils.get_disk_attachments_service(engine, BACKUP_VM_NAME)

    with engine_utils.wait_for_event(engine, 2016):  # USER_ATTACH_DISK_TO_VM event
        disk_attachments_service.add(
            types.DiskAttachment(
                disk=types.Disk(
                    id=vm2_disk.id,
                    snapshot=types.Snapshot(id=vm2_snapshots_service.list()[-1].id),
                ),
                interface=types.DiskInterface.VIRTIO_SCSI,
                bootable=False,
                active=True,
            )
        )
        assert len(disk_attachments_service.list()) > 0


@order_by(_TEST_LIST)
def test_remove_vm2_backup_checkpoints(engine_api, get_vm_service_for_vm):
    # Removing all the checkpoints created during backup tests
    # to prevent testing QEMU crash that will cause inconsistent bitmaps,
    # so the disk migration will failed - https://bugzilla.redhat.com/1946084.
    vm2_service = _verify_vm_state(engine_api.system_service(), VM2_NAME, types.VmStatus.UP)
    vm2_checkpoints_service = vm2_service.checkpoints_service()
    for _ in vm2_checkpoints_service.list():
        backup.remove_vm_root_checkpoint(vm2_checkpoints_service)


@pytest.fixture(scope="session")
def vm0_fqdn_or_ip(tested_ip_version, management_subnet):
    vm0_address = {'ipv4': VM0_NAME, 'ipv6': str(management_subnet[250])}
    return vm0_address[f'ipv{tested_ip_version}']


@order_by(_TEST_LIST)
def test_verify_transient_folder(assert_vm_is_alive, engine_api, get_ansible_host_for_vm, vm0_fqdn_or_ip):
    engine = engine_api.system_service()
    sd = engine.storage_domains_service().list(search='name={}'.format(SD_SECOND_NFS_NAME))[0]
    ansible_host = get_ansible_host_for_vm(BACKUP_VM_NAME)
    out = ansible_host.shell('ls /var/lib/vdsm/transient')['stdout']

    all_volumes = out.strip().splitlines()
    assert len(all_volumes) == 1

    assert sd.id in all_volumes[0]
    assert_vm_is_alive(vm0_fqdn_or_ip)


@order_by(_TEST_LIST)
def test_verify_and_remove_cloned_vm(system_service, get_disk_services_for_vm_or_template, get_vm_service_for_vm):
    correlation_id = 'clone_powered_off_vm'

    assert assert_utils.true_within_short(lambda: test_utils.all_jobs_finished(system_service, correlation_id))

    cloned_vm_service = _verify_vm_state(system_service, CLONED_VM_NAME, types.VmStatus.DOWN)
    _verify_vm_disks_state(
        CLONED_VM_NAME, types.DiskStatus.OK, get_disk_services_for_vm_or_template, get_vm_service_for_vm
    )

    vm_to_clone_snapshots_service = test_utils.get_vm_snapshots_service(system_service, VM_TO_CLONE_NAME)
    assert assert_utils.equals_within_short(lambda: len(vm_to_clone_snapshots_service.list()), 1)

    num_of_vms = len(system_service.vms_service().list())
    vm_to_clone_service = test_utils.get_vm_service(system_service, VM_TO_CLONE_NAME)
    vm_to_clone_service.remove(detach_only=True)
    cloned_vm_service.remove()
    assert len(system_service.vms_service().list()) == (num_of_vms - 2)
    floating_disk_service = test_utils.get_disk_service(system_service, FLOATING_DISK_NAME)
    assert floating_disk_service is not None


@order_by(_TEST_LIST)
def test_remove_backup_vm_and_backup_snapshot(engine_api):
    engine = engine_api.system_service()
    backup_vm_service = test_utils.get_vm_service(engine, BACKUP_VM_NAME)
    vm2_snapshots_service = test_utils.get_vm_snapshots_service(engine, VM2_NAME)
    vm2_snapshot = vm2_snapshots_service.list()[-1]
    # power-off backup-vm
    with engine_utils.wait_for_event(engine, [33, 61]):
        # VM_DOWN(61) event
        # USER_STOP_VM(33) event
        backup_vm_service.stop()
        assert assert_utils.equals_within_long(lambda: backup_vm_service.get().status, types.VmStatus.DOWN)
    # remove backup_vm
    num_of_vms = len(engine.vms_service().list())
    backup_vm_service.remove()
    assert len(engine.vms_service().list()) == (num_of_vms - 1)
    with engine_utils.wait_for_event(engine, 342):  # USER_REMOVE_SNAPSHOT event
        # remove vm2 snapshot
        vm2_snapshots_service.snapshot_service(vm2_snapshot.id).remove()


@order_by(_TEST_LIST)
def test_verify_backup_snapshot_removed(engine_api):
    engine = engine_api.system_service()
    vm2_snapshots_service = test_utils.get_vm_snapshots_service(engine, VM2_NAME)

    assert assert_utils.equals_within_long(lambda: len(vm2_snapshots_service.list()), 1)


def snapshot_cold_merge(engine_api):
    engine = engine_api.system_service()
    vm1_snapshots_service = test_utils.get_vm_snapshots_service(engine, VM1_NAME)

    disk = engine.disks_service().list(search='name={} and vm_names={}'.format(DISK1_NAME, VM1_NAME))[0]

    dead_snap1_params = types.Snapshot(
        description=SNAPSHOT_DESC_1,
        persist_memorystate=False,
        disk_attachments=[types.DiskAttachment(disk=types.Disk(id=disk.id))],
    )
    correlation_id = uuid.uuid4()

    vm1_snapshots_service.add(dead_snap1_params, query={'correlation_id': correlation_id})

    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))
    assert assert_utils.equals_within_long(
        lambda: vm1_snapshots_service.list()[-1].snapshot_status,
        types.SnapshotStatus.OK,
    )

    dead_snap2_params = types.Snapshot(
        description=SNAPSHOT_DESC_2,
        persist_memorystate=False,
        disk_attachments=[types.DiskAttachment(disk=types.Disk(id=disk.id))],
    )
    correlation_id_snap2 = uuid.uuid4()

    vm1_snapshots_service.add(dead_snap2_params, query={'correlation_id': correlation_id_snap2})

    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id_snap2))
    assert assert_utils.equals_within_long(
        lambda: vm1_snapshots_service.list()[-1].snapshot_status,
        types.SnapshotStatus.OK,
    )

    snapshot = vm1_snapshots_service.list()[-2]
    vm1_snapshots_service.snapshot_service(snapshot.id).remove()

    assert assert_utils.equals_within_long(lambda: len(vm1_snapshots_service.list()), 2)
    assert assert_utils.equals_within_long(
        lambda: vm1_snapshots_service.list()[-1].snapshot_status,
        types.SnapshotStatus.OK,
    )


@order_by(_TEST_LIST)
def test_make_snapshot_with_memory(engine_api):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    disks_service = engine.disks_service()
    vm_disks_service = test_utils.get_disk_attachments_service(engine, VM0_NAME)
    vm_disks = [disks_service.disk_service(attachment.disk.id).get() for attachment in vm_disks_service.list()]
    disk_attachments = [
        types.DiskAttachment(disk=types.Disk(id=disk.id))
        for disk in vm_disks
        if disk.storage_type != types.DiskStorageType.LUN
    ]
    snapshots_service = vm_service.snapshots_service()
    snapshot_params = types.Snapshot(
        description=SNAPSHOT_DESC_MEM,
        persist_memorystate=True,
        disk_attachments=disk_attachments,
    )
    correlation_id = "make_preview_snapshot_with_memory"
    with engine_utils.wait_for_event(engine, 45):  # USER_CREATE_SNAPSHOT event
        snapshots_service.add(snapshot_params, query={'correlation_id': correlation_id})


@order_by(_TEST_LIST)
def test_preview_snapshot_with_memory(engine_api):
    engine = engine_api.system_service()
    correlation_id = "make_preview_snapshot_with_memory"
    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    vm_service.stop()
    _verify_vm_state(engine, VM0_NAME, types.VmStatus.DOWN)
    snapshot = test_utils.get_snapshot(engine, VM0_NAME, SNAPSHOT_DESC_MEM)
    vm_service.preview_snapshot(snapshot=snapshot, async_=False, restore_memory=True)


@order_by(_TEST_LIST)
def test_vmconsole(engine_api, engine_ip, working_dir, rsa_pair):
    engine = engine_api.system_service()
    vms_service = engine.vms_service()
    vm0_id = vms_service.list(search=f'name={VM0_NAME}')[0].id

    master, slave = pty.openpty()
    vmconsole_process = subprocess.Popen(
        [
            'ssh',
            '-t',
            '-o',
            'StrictHostKeyChecking=no',
            '-i',
            f'{rsa_pair[1]}',
            '-p',
            '2222',
            f'ovirt-vmconsole@{engine_ip}',
            'connect',
            f'--vm-id={vm0_id}',
        ],
        stdin=slave,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=0,
    )

    vmconsole_in = os.fdopen(master, 'w')
    connection_success = False
    for i in range(30):
        vmconsole_in.write('\n')
        response = vmconsole_process.stdout.read(1)
        if len(response.strip()) != 0:
            message = response + vmconsole_process.stdout.readline()
            if f"login as '{VM_USER_NAME}'" in message or f'{VM0_NAME} login' in message:
                connection_success = True
                break
        sleep(1)
    vmconsole_process.terminate()
    # The test fails if the connection to vmconsole was unsuccessful after 30 seconds
    assert connection_success


@order_by(_TEST_LIST)
def test_check_snapshot_with_memory(engine_api):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    assert assert_utils.equals_within_long(
        lambda: test_utils.get_snapshot(engine, VM0_NAME, SNAPSHOT_DESC_MEM).snapshot_status,
        types.SnapshotStatus.IN_PREVIEW,
    )
    vm_service.start()
    _verify_vm_state(engine, VM0_NAME, types.VmStatus.UP)


def cold_storage_migration(engine_api):
    engine = engine_api.system_service()
    disk_service = test_utils.get_disk_service(engine, DISK2_NAME)

    # Cold migrate the disk to ISCSI storage domain and then migrate it back
    # to the NFS domain because it is used by other cases that assume the
    # disk found on that specific domain
    for domain in [SD_ISCSI_NAME, SD_SECOND_NFS_NAME]:
        with engine_utils.wait_for_event(engine, 2008):  # USER_MOVED_DISK(2,008)
            disk_service.move(async_=False, storage_domain=types.StorageDomain(name=domain))

            assert assert_utils.equals_within_long(
                lambda: engine_api.follow_link(disk_service.get().storage_domains[0]).name,
                domain,
            )
            assert assert_utils.equals_within_long(lambda: disk_service.get().status, types.DiskStatus.OK)


@order_by(_TEST_LIST)
def test_live_storage_migration(engine_api):
    engine = engine_api.system_service()
    disk_service = test_utils.get_disk_service(engine, DISK0_NAME)
    correlation_id = 'live_storage_migration'
    disk_service.move(
        async_=False,
        filter=False,
        storage_domain=types.StorageDomain(name=SD_ISCSI_NAME),
        query={'correlation_id': correlation_id},
    )

    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))

    # Assert that the disk is on the correct storage domain,
    # its status is OK and the snapshot created for the migration
    # has been merged
    assert assert_utils.equals_within_long(
        lambda: engine_api.follow_link(disk_service.get().storage_domains[0]).name,
        SD_ISCSI_NAME,
    )

    vm0_snapshots_service = test_utils.get_vm_snapshots_service(engine, VM0_NAME)
    assert assert_utils.equals_within_long(lambda: len(vm0_snapshots_service.list()), 1)
    assert assert_utils.equals_within_long(lambda: disk_service.get().status, types.DiskStatus.OK)


@order_by(_TEST_LIST)
def test_export_vm2(engine_api):
    engine = engine_api.system_service()
    vm_service = _verify_vm_state(engine, VM2_NAME, types.VmStatus.UP)
    host = test_utils.get_first_active_host_by_name(engine)

    with engine_utils.wait_for_event(engine, 1223):  # IMPORTEXPORT_STARTING_EXPORT_VM_TO_OVA event
        vm_service.export_to_path_on_host(
            host=types.Host(id=host.id),
            directory=OVA_DIR,
            filename=OVA_VM_EXPORT_NAME,
            async_=True,
        )


@order_by(_TEST_LIST)
def test_verify_vm2_exported(engine_api):
    engine = engine_api.system_service()
    vm1_snapshots_service = test_utils.get_vm_snapshots_service(engine, VM2_NAME)
    assert assert_utils.equals_within_long(lambda: len(vm1_snapshots_service.list()), 1)
    # ...and it should still be running
    _verify_vm_state(engine_api.system_service(), VM2_NAME, types.VmStatus.UP)


@order_by(_TEST_LIST)
def test_verify_template_exported(engine_api, cirros_image_template_name):
    engine = engine_api.system_service()
    correlation_id = "test_validate_ova_export_temp"
    template_service = test_utils.get_template_service(engine, cirros_image_template_name)
    if template_service is None:
        pytest.skip(
            '{0}: template {1} is missing'.format(
                test_verify_template_exported.__name__,
                cirros_image_template_name,
            )
        )
    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))


@order_by(_TEST_LIST)
def test_import_vm_preallocated(engine_api, ost_cluster_name):
    engine = engine_api.system_service()
    sd = engine.storage_domains_service().list(search='name={}'.format(SD_ISCSI_NAME))[0]
    cluster = engine.clusters_service().list(search='name={}'.format(ost_cluster_name))[0]
    imports_service = engine.external_vm_imports_service()
    host = test_utils.get_first_active_host_by_name(engine)
    correlation_id = "test_validate_ova_import_vm"

    with engine_utils.wait_for_event(engine, 1165):  # IMPORTEXPORT_STARTING_IMPORT_VM
        imports_service.add(
            types.ExternalVmImport(
                name=IMPORTED_VM_NAME,
                provider=types.ExternalVmProviderType.KVM,
                url=IMPORTED_OVA_NAME,
                cluster=types.Cluster(id=cluster.id),
                storage_domain=types.StorageDomain(id=sd.id),
                host=types.Host(id=host.id),
            ),
            async_=True,
            query={'correlation_id': correlation_id},
        )


@order_by(_TEST_LIST)
def test_verify_vm_import_preallocated(engine_api, get_vm_service_for_vm, get_disk_services_for_vm_or_template):
    engine = engine_api.system_service()
    correlation_id = "test_validate_ova_import_vm"

    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))
    assert assert_utils.true_within_short(lambda: test_utils.get_vm_service(engine, IMPORTED_VM_NAME) is not None)

    vm_service = get_vm_service_for_vm(IMPORTED_VM_NAME)
    disks_service = get_disk_services_for_vm_or_template(vm_service)

    assert assert_utils.true_within_short(
        lambda: all(
            disk_service.get().sparse == False
            # pylint: disable=not-an-iterable
            for disk_service in disks_service
        )
    )


@order_by(_TEST_LIST)
def test_import_template(engine_api, ost_cluster_name):
    engine = engine_api.system_service()
    sd = engine.storage_domains_service().list(search='name={}'.format(SD_NFS_NAME))[0]
    cluster = engine.clusters_service().list(search='name={}'.format(ost_cluster_name))[0]
    imports_service = engine.external_template_imports_service()
    host = test_utils.get_first_active_host_by_name(engine)
    correlation_id = "test_validate_ova_import_temp"

    with engine_utils.wait_for_event(engine, 1163):  # IMPORTEXPORT_STARTING_IMPORT_TEMPLATE
        imports_service.add(
            types.ExternalTemplateImport(
                template=types.Template(name=IMPORTED_TEMP_NAME),
                url=IMPORTED_TEMP_OVA_NAME,
                cluster=types.Cluster(id=cluster.id),
                storage_domain=types.StorageDomain(id=sd.id),
                host=types.Host(id=host.id),
                clone=True,
            ),
            async_=True,
            query={'correlation_id': correlation_id},
        )


@order_by(_TEST_LIST)
def test_verify_template_import(engine_api, get_template_service_for_template, get_disk_services_for_vm_or_template):
    engine = engine_api.system_service()
    correlation_id = "test_validate_ova_import_temp"

    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))
    assert assert_utils.true_within_short(
        lambda: test_utils.get_template_service(engine, IMPORTED_TEMP_NAME) is not None
    )

    template_service = get_template_service_for_template(IMPORTED_TEMP_NAME)
    disks_service = get_disk_services_for_vm_or_template(template_service)

    assert assert_utils.true_within_short(
        lambda: all(
            disk_service.get().sparse == True
            # pylint: disable=not-an-iterable
            for disk_service in disks_service
        )
    )


@order_by(_TEST_LIST)
def test_add_vm1_from_template(engine_api, cirros_image_template_name, ost_cluster_name):
    engine = engine_api.system_service()
    templates_service = engine.templates_service()
    cirros_template = templates_service.list(search='name=%s' % cirros_image_template_name)[0]
    if cirros_template is None:
        pytest.skip(
            '%s: template %s not available.'
            % (
                test_add_vm1_from_template.__name__,
                cirros_image_template_name,
            )
        )

    vm_memory = 128 * MB  # runs with 64 ok, but we need to do a hotplug later (64+256 is too much difference)
    vms_service = engine.vms_service()
    vms_service.add(
        types.Vm(
            name=VM1_NAME,
            description='CirrOS imported as Template',
            memory=vm_memory,
            cluster=types.Cluster(
                name=ost_cluster_name,
            ),
            template=types.Template(
                name=cirros_image_template_name,
            ),
            use_latest_template_version=True,
            stateless=True,
            memory_policy=types.MemoryPolicy(
                guaranteed=vm_memory,  # with so little memory we don't want guaranteed to be any lower
                ballooning=False,
            ),
            os=types.OperatingSystem(
                type='rhel_7x64',  # even though it's CirrOS we want to check a non-default OS type
            ),
            time_zone=types.TimeZone(
                name='Etc/GMT',
            ),
            type=types.VmType.SERVER,
            serial_number=types.SerialNumber(
                policy=types.SerialNumberPolicy.CUSTOM,
                value='12345678',
            ),
            cpu=types.Cpu(
                architecture=types.Architecture.X86_64,
                topology=types.CpuTopology(
                    sockets=1,
                    cores=1,
                    threads=2,
                ),
            ),
        )
    )


@order_by(_TEST_LIST)
def test_verify_add_vm1_from_template(engine_api, get_disk_services_for_vm_or_template, get_vm_service_for_vm):
    engine = engine_api.system_service()
    _verify_vm_state(engine, VM1_NAME, types.VmStatus.DOWN)
    _verify_vm_disks_state(
        VM1_NAME,
        types.DiskStatus.OK,
        get_disk_services_for_vm_or_template,
        get_vm_service_for_vm,
    )


@order_by(_TEST_LIST)
def test_cold_incremental_backup_vm2(engine_api, get_vm_service_for_vm):
    vm2_service = _verify_vm_state(engine_api.system_service(), VM2_NAME, types.VmStatus.DOWN)
    vm2_backups_service = vm2_service.backups_service()
    backup.perform_incremental_vm_backup(engine_api, vm2_backups_service, DISK2_NAME, "cold_vm_backup")


@order_by(_TEST_LIST)
def test_run_vms(
    assert_vm_is_alive,
    engine_api,
    management_gw_ip,
    vm0_fqdn_or_ip,
    tested_ip_version,
    cirros_serial_console,
):
    engine = engine_api.system_service()

    vm_params = types.Vm(initialization=types.Initialization(user_name=VM_USER_NAME, root_password=VM_PASSWORD))

    vm_params.initialization.host_name = BACKUP_VM_NAME
    backup_vm_service = test_utils.get_vm_service(engine, BACKUP_VM_NAME)
    backup_vm_service.start(use_cloud_init=True, vm=vm_params)

    vm_params.initialization.host_name = VM2_NAME
    vm2_service = test_utils.get_vm_service(engine, VM2_NAME)
    vm2_service.start(use_cloud_init=True, vm=vm_params)

    # CirrOS cloud-init is different, networking doesn't work since it doesn't support the format oVirt is using
    vm_params.initialization.host_name = VM0_NAME  # hostname seems to work, the others not
    vm_params.initialization.dns_search = 'lago.local'
    vm_params.initialization.domain = 'lago.local'
    vm_params.initialization.dns_servers = str(management_gw_ip)
    vm0_service = test_utils.get_vm_service(engine, VM0_NAME)
    vm0_service.start(use_cloud_init=True, vm=vm_params)

    for vm_name in [VM0_NAME, BACKUP_VM_NAME]:
        _verify_vm_state(engine, vm_name, types.VmStatus.UP)

    if tested_ip_version == 6:
        vms_service = engine_api.system_service().vms_service()
        vm = vms_service.list(search='name={}'.format(VM0_NAME))[0]
        cirros_serial_console.add_static_ip(vm.id, f'{vm0_fqdn_or_ip}/64', 'eth0')

    assert_vm_is_alive(vm0_fqdn_or_ip)


@order_by(_TEST_LIST)
def test_verify_vm2_run(engine_api):
    _verify_vm_state(engine_api.system_service(), VM2_NAME, types.VmStatus.UP)


@order_by(_TEST_LIST)
def test_live_incremental_backup_vm2(engine_api, get_vm_service_for_vm):
    vm2_service = _verify_vm_state(engine_api.system_service(), VM2_NAME, types.VmStatus.UP)
    vm2_backups_service = vm2_service.backups_service()
    backup.perform_incremental_vm_backup(engine_api, vm2_backups_service, DISK2_NAME, "live_vm_backup")


@order_by(_TEST_LIST)
def test_vm0_is_alive(assert_vm_is_alive, vm0_fqdn_or_ip):
    assert_vm_is_alive(vm0_fqdn_or_ip)


@pytest.fixture(scope="module")
def ansible_host_for_vm2(get_ansible_host_for_vm):
    return get_ansible_host_for_vm(VM2_NAME)


@pytest.fixture(scope="module")
def qemu_pid_for_vm2(ansible_host_for_vm2):
    pgrep_res = ansible_host_for_vm2.shell('pgrep -f qemu.*guest=vm2')
    return int(pgrep_res['stdout'].strip())


@order_by(_TEST_LIST)
def test_ha_recovery(engine_api, qemu_pid_for_vm2, ansible_host_for_vm2):
    engine = engine_api.system_service()
    with engine_utils.wait_for_event(engine, [119, 9602, 506]):
        # VM_DOWN_ERROR event(119)
        # HA_VM_FAILED event event(9602)
        # VDS_INITIATED_RUN_VM event(506)
        LOGGER.debug(f'test_ha_recovery: ansible_host={ansible_host_for_vm2}')
        LOGGER.debug(f'test_ha_recovery: pid={qemu_pid_for_vm2}')
        abrt_res = ansible_host_for_vm2.shell(f'/usr/bin/kill -s SIGABRT {qemu_pid_for_vm2}')
        LOGGER.debug(f'SIGABRT_res={abrt_res}')

    vm_service = test_utils.get_vm_service(engine, VM2_NAME)
    assert assert_utils.equals_within_long(lambda: vm_service.get().status, types.VmStatus.UP)
    with engine_utils.wait_for_event(engine, 33):  # USER_STOP_VM event
        vm_service.stop()


@order_by(_TEST_LIST)
def test_check_coredump_generated(qemu_pid_for_vm2, ansible_host_for_vm2):
    # this test depends on "test_ha_recovery" kill signal
    ansible_host_for_vm2.shell(f'coredumpctl list {qemu_pid_for_vm2}')


@order_by(_TEST_LIST)
def test_offline_snapshot_restore(engine_api):
    engine = engine_api.system_service()
    vm_service = _verify_vm_state(engine, VM2_NAME, types.VmStatus.DOWN)
    disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM2_NAME)
    disk = disk_attachments_service.list()[0]
    snapshots_service = vm_service.snapshots_service()

    snapshot_params = types.Snapshot(
        description=SNAPSHOT_DESC_OFF,
        persist_memorystate=False,
        disk_attachments=[types.DiskAttachment(disk=types.Disk(id=disk.id))],
    )
    with engine_utils.wait_for_event(engine, [45, 68]):
        # USER_CREATE_SNAPSHOT event - 45
        # USER_CREATE_SNAPSHOT_FINISHED_SUCCESS - 68
        snapshots_service.add(snapshot_params)
    snapshot = test_utils.get_snapshot(engine, VM2_NAME, SNAPSHOT_DESC_OFF)
    with engine_utils.wait_for_event(engine, [46, 71]):
        # USER_TRY_BACK_TO_SNAPSHOT - 46
        # USER_TRY_BACK_TO_SNAPSHOT_FINISH_SUCCESS - 71
        vm_service.preview_snapshot(snapshot=snapshot, async_=False, restore_memory=False)
    assert assert_utils.equals_within_short(
        lambda: test_utils.get_snapshot(engine, VM2_NAME, SNAPSHOT_DESC_OFF).snapshot_status,
        types.SnapshotStatus.IN_PREVIEW,
    )
    vm_service.start()


@order_by(_TEST_LIST)
def test_verify_offline_snapshot_restore(engine_api):
    engine = engine_api.system_service()

    vm_service = _verify_vm_state(engine, VM2_NAME, types.VmStatus.UP)
    vm_service.stop()
    _verify_vm_state(engine, VM2_NAME, types.VmStatus.DOWN)
    with engine_utils.wait_for_event(engine, [94, 95]):
        # USER_COMMIT_RESTORE_FROM_SNAPSHOT_START - 94
        # USER_COMMIT_RESTORE_FROM_SNAPSHOT_FINISH_SUCCESS - 95
        vm_service.commit_snapshot(async_=False)


@order_by(_TEST_LIST)
def test_vdsm_recovery(system_service, hosts_service, ost_dc_name, ansible_by_hostname):
    vm_service = test_utils.get_vm_service(system_service, VM0_NAME)
    host_id = vm_service.get().host.id
    host_service = hosts_service.host_service(host_id)
    host_name = host_service.get().name
    ansible_host = ansible_by_hostname(host_name)

    # TODO masking - ugly workaround for https://bugzilla.redhat.com/2029030
    ansible_host.systemd(name='vdsmd', state='stopped', masked='yes')
    assert assert_utils.equals_within_short(lambda: vm_service.get().status, types.VmStatus.UNKNOWN)

    ansible_host.systemd(name='vdsmd', state='started', masked='no')
    assert assert_utils.equals_within_short(lambda: host_service.get().status, types.HostStatus.UP)

    host_utils.wait_for_flapping_host(hosts_service, ost_dc_name, host_id)

    assert assert_utils.equals_within_short(lambda: vm_service.get().status, types.VmStatus.UP)


@order_by(_TEST_LIST)
def test_template_export(engine_api, cirros_image_template_name):
    engine = engine_api.system_service()

    template_service = test_utils.get_template_service(engine, cirros_image_template_name)
    if template_service is None:
        pytest.skip(
            '{0}: template {1} is missing'.format(
                test_template_export.__name__,
                cirros_image_template_name,
            )
        )
    host = test_utils.get_first_active_host_by_name(engine)
    correlation_id = "test_validate_ova_export_temp"
    with engine_utils.wait_for_event(engine, 1226):
        # IMPORTEXPORT_STARTING_EXPORT_TEMPLATE_TO_OVA event
        template_service.export_to_path_on_host(
            host=types.Host(id=host.id),
            directory=OVA_DIR,
            filename=OVA_TEMP_EXPORT_NAME,
            async_=True,
            query={'correlation_id': correlation_id},
        )


@order_by(_TEST_LIST)
def test_add_vm_pool(engine_api, cirros_image_template_name, ost_cluster_name):
    engine = engine_api.system_service()
    pools_service = engine.vm_pools_service()
    pool_cluster = engine.clusters_service().list(search='name={}'.format(ost_cluster_name))[0]
    pool_template = engine.templates_service().list(search='name={}'.format(cirros_image_template_name))[0]
    with engine_utils.wait_for_event(engine, 302):
        pools_service.add(
            pool=types.VmPool(
                name=VMPOOL_NAME,
                cluster=pool_cluster,
                template=pool_template,
                use_latest_template_version=True,
            )
        )
    vm_service = test_utils.get_vm_service(engine, VMPOOL_NAME + '-1')
    assert assert_utils.equals_within_short(
        lambda: vm_service.get().status,
        types.VmStatus.DOWN,
        allowed_exceptions=[IndexError],
    )


@order_by(_TEST_LIST)
def test_verify_ovf_import(engine_api, get_disk_services_for_vm_or_template, get_vm_service_for_vm):
    engine = engine_api.system_service()
    _verify_vm_state(engine, OVF_VM_NAME, types.VmStatus.DOWN)
    _verify_vm_disks_state(
        OVF_VM_NAME, types.DiskStatus.OK, get_disk_services_for_vm_or_template, get_vm_service_for_vm
    )


@order_by(_TEST_LIST)
def test_update_template_version(engine_api, cirros_image_template_name, cirros_image_template_version_name):
    engine = engine_api.system_service()
    ovf_vm = test_utils.get_vm_service(engine, OVF_VM_NAME).get()
    templates_service = engine.templates_service()
    template_service = test_utils.get_template_service(engine, cirros_image_template_name)
    template = template_service.get()

    assert ovf_vm.memory != template.memory

    templates_service.add(
        template=types.Template(
            name=cirros_image_template_name,
            vm=ovf_vm,
            version=types.TemplateVersion(
                base_template=template,
                version_name=cirros_image_template_version_name,
            ),
        )
    )
    pool_service = test_utils.get_pool_service(engine, VMPOOL_NAME)
    assert assert_utils.equals_within_long(lambda: pool_service.get().vm.memory, ovf_vm.memory)


@order_by(_TEST_LIST)
def test_verify_update_template_version(
    engine_api,
    cirros_image_template_name,
    cirros_image_template_version_name,
    get_disk_services_for_vm_or_template,
    get_vm_service_for_vm,
):
    engine = engine_api.system_service()
    templates_service = engine.templates_service()
    template_version = templates_service.list(
        search='name={} and version_name={}'.format(
            cirros_image_template_name,
            cirros_image_template_version_name,
        )
    )[0]
    vm_name = VMPOOL_NAME + '-1'
    vm_service = test_utils.get_vm_service(engine, vm_name)
    assert assert_utils.equals_within_long(lambda: vm_service.get().template.id, template_version.id)
    _verify_vm_state(engine, vm_name, types.VmStatus.DOWN)
    _verify_vm_disks_state(vm_name, types.DiskStatus.OK, get_disk_services_for_vm_or_template, get_vm_service_for_vm)


@order_by(_TEST_LIST)
def test_update_vm_pool(engine_api):
    engine = engine_api.system_service()
    pool_service = test_utils.get_pool_service(engine, VMPOOL_NAME)
    correlation_id = uuid.uuid4()
    pool_service.update(
        pool=types.VmPool(max_user_vms=2),
        query={'correlation_id': correlation_id},
    )
    assert pool_service.get().max_user_vms == 2
    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))


@versioning.require_version(4, 1)
@order_by(_TEST_LIST)
def test_remove_vm2_lease(engine_api):
    engine = engine_api.system_service()
    vm2_service = test_utils.get_vm_service(engine, VM2_NAME)

    vm2_service.update(
        vm=types.Vm(
            high_availability=types.HighAvailability(
                enabled=False,
            ),
            lease=types.StorageDomainLease(storage_domain=None),
        )
    )
    assert assert_utils.true_within_short(lambda: vm2_service.get().lease is None)


@order_by(_TEST_LIST)
def test_remove_vm_pool(engine_api):
    engine = engine_api.system_service()
    pool_service = test_utils.get_pool_service(engine, VMPOOL_NAME)
    correlation_id = uuid.uuid4()
    with engine_utils.wait_for_event(engine, [321, 304]):
        # USER_REMOVE_VM_POOL_INITIATED(321) event
        # USER_REMOVE_VM_POOL(304) event
        pool_service.remove(query={'correlation_id': correlation_id})
        vm_pools_service = engine_api.system_service().vm_pools_service()
        assert len(vm_pools_service.list()) == 0
    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))


@order_by(_TEST_LIST)
def test_template_update(engine_api, cirros_image_template_name):
    template_guest = test_utils.get_template_service(engine_api.system_service(), cirros_image_template_name)

    if template_guest is None:
        pytest.skip(
            '{0}: template {1} is missing'.format(
                test_template_update.__name__,
                cirros_image_template_name,
            )
        )
    new_comment = "comment by ovirt-system-tests"
    template_guest.update(template=types.Template(comment=new_comment))
    assert assert_utils.equals_within_short(lambda: template_guest.get().status, types.TemplateStatus.OK)
    assert template_guest.get().comment == new_comment


@order_by(_TEST_LIST)
def test_disk_operations(engine_api):
    vt = utils.VectorThread(
        [
            functools.partial(cold_storage_migration, engine_api),
            functools.partial(snapshot_cold_merge, engine_api),
        ],
    )
    vt.start_all()
    vt.join_all()


@pytest.fixture(scope="session")
def hotplug_mem_amount():
    return 256 * MB


@pytest.fixture(scope="session")
def get_vm_libvirt_memory_amount(get_vm_libvirt_xml):
    def mem_amount(vm_name):
        xml = get_vm_libvirt_xml(vm_name)
        match = re.search(r'<currentMemory unit=\'KiB\'>(?P<mem>[0-9]+)', xml)
        return int(match.group('mem'))

    return mem_amount


@order_by(_TEST_LIST)
def test_hotplug_memory(
    assert_vm_is_alive,
    engine_api,
    get_vm_libvirt_memory_amount,
    hotplug_mem_amount,
    vm0_fqdn_or_ip,
):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    new_memory = vm_service.get().memory + hotplug_mem_amount
    with engine_utils.wait_for_event(engine, 2039):  # HOT_SET_MEMORY(2,039)
        vm_service.update(
            vm=types.Vm(
                memory=new_memory,
                # Need to avoid OOM scenario where ballooning would immediately try to claim some memory.
                # CirrOS is lacking memory onlining rules so the guest memory doesn't really increase and
                # balloon inflation just crashes the guest instead. Balloon gets inflated because MOM
                # does not know that guest size didn't increase and just assumes it did, and the host
                # OST VM is likely under memory pressure, there's not much free RAM in OST environment.
                # Setting minimum guaranteed to new memory size keeps MOM from inflating balloon.
                memory_policy=types.MemoryPolicy(
                    guaranteed=new_memory,
                ),
            )
        )
        assert vm_service.get().memory == new_memory

    assert_vm_is_alive(vm0_fqdn_or_ip)
    assert get_vm_libvirt_memory_amount(VM0_NAME) // KB == new_memory // MB


@order_by(_TEST_LIST)
def test_hotunplug_memory(
    assert_vm_is_alive,
    engine_api,
    get_vm_libvirt_memory_amount,
    hotplug_mem_amount,
    vm0_fqdn_or_ip,
):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    new_memory = vm_service.get().memory - hotplug_mem_amount
    with engine_utils.wait_for_event(engine, 2046):  # MEMORY_HOT_UNPLUG_SUCCESSFULLY_REQUESTED(2,046)
        vm_service.update(
            vm=types.Vm(
                memory=new_memory,
                memory_policy=types.MemoryPolicy(
                    guaranteed=new_memory,
                ),
            )
        )
        assert vm_service.get().memory == new_memory

    assert_vm_is_alive(vm0_fqdn_or_ip)
    assert get_vm_libvirt_memory_amount(VM0_NAME) // KB == new_memory // MB


@order_by(_TEST_LIST)
def test_hotplug_cpu(engine_api, vm_ssh, vm0_fqdn_or_ip):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    new_cpu = vm_service.get().cpu
    new_cpu.topology.sockets = 2
    with engine_utils.wait_for_event(engine, 2033):  # HOT_SET_NUMBER_OF_CPUS(2,033)
        vm_service.update(vm=types.Vm(cpu=new_cpu))
        assert vm_service.get().cpu.topology.sockets == 2
    ret = vm_ssh(vm0_fqdn_or_ip, 'lscpu')
    assert ret.code == 0
    match = re.search(r'CPU\(s\):\s+(?P<cpus>[0-9]+)', ret.out.decode('utf-8'))
    assert match.group('cpus') == '2'


@order_by(_TEST_LIST)
def test_next_run_unplug_cpu(engine_api):
    engine = engine_api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    new_cpu = vm_service.get().cpu
    new_cpu.topology.sockets = 1
    vm_service.update(
        vm=types.Vm(
            cpu=new_cpu,
        ),
        next_run=True,
    )
    assert vm_service.get().cpu.topology.sockets == 2
    assert vm_service.get(next_run=True).cpu.topology.sockets == 1

    with engine_utils.wait_for_event(engine, 157):  # USER_REBOOT_VM(157)
        vm_service.reboot()
        assert assert_utils.equals_within_long(lambda: vm_service.get().status, types.VmStatus.UP)
    assert vm_service.get().cpu.topology.sockets == 1


@order_by(_TEST_LIST)
def test_hotplug_nic(assert_vm_is_alive, engine_api, vm0_fqdn_or_ip):
    vms_service = engine_api.system_service().vms_service()
    vm = vms_service.list(search='name=%s' % VM0_NAME)[0]
    nics_service = vms_service.vm_service(vm.id).nics_service()
    nics_service.add(
        types.Nic(name='eth1', interface=types.NicInterface.VIRTIO),
    )
    assert_vm_is_alive(vm0_fqdn_or_ip)


@order_by(_TEST_LIST)
def test_hotplug_disk(assert_vm_is_alive, engine_api, vm0_fqdn_or_ip):
    engine = engine_api.system_service()
    disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM0_NAME)
    disk_attachment = disk_attachments_service.add(
        types.DiskAttachment(
            disk=types.Disk(
                name=DISK0_NAME,
                provisioned_size=2 * GB,
                format=types.DiskFormat.COW,
                storage_domains=[
                    types.StorageDomain(
                        name=SD_NFS_NAME,
                    ),
                ],
                status=None,
                sparse=True,
            ),
            # FIXME - move back to VIRTIO once we have a libvirt fix for
            # https://bugzilla.redhat.com/1970277
            interface=types.DiskInterface.VIRTIO_SCSI,
            bootable=False,
            active=True,
        )
    )

    disks_service = engine.disks_service()
    disk_service = disks_service.disk_service(disk_attachment.disk.id)
    attachment_service = disk_attachments_service.attachment_service(disk_attachment.id)

    assert assert_utils.true_within_short(lambda: attachment_service.get().active)
    assert assert_utils.equals_within_short(lambda: disk_service.get().status, types.DiskStatus.OK)
    assert_vm_is_alive(vm0_fqdn_or_ip)


@order_by(_TEST_LIST)
def test_hotunplug_disk(engine_api):
    engine = engine_api.system_service()
    disk_service = test_utils.get_disk_service(engine, DISK0_NAME)
    disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM0_NAME)
    disk_attachment = disk_attachments_service.attachment_service(disk_service.get().id)

    with engine_utils.wait_for_event(engine, 2002):
        # USER_HOTUNPLUG_DISK(2,002)
        correlation_id = 'test_hotunplug_disk'
        assert disk_attachment.update(
            types.DiskAttachment(active=False),
            query={'correlation_id': correlation_id},
        )
        assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(engine, correlation_id))

        assert assert_utils.equals_within_short(lambda: disk_service.get().status, types.DiskStatus.OK)

        assert assert_utils.equals_within_short(lambda: disk_attachment.get().active, False)


@order_by(_TEST_LIST)
def test_suspend_resume_vm0(assert_vm_is_alive, engine_api, vm_ssh, vm0_fqdn_or_ip):
    # start a background job we are going to check if it's still running later
    ret = vm_ssh(vm0_fqdn_or_ip, 'sleep 3600 &')
    assert ret.code == EX_OK

    assert_vm_is_alive(vm0_fqdn_or_ip)

    vm_service = test_utils.get_vm_service(engine_api.system_service(), VM0_NAME)
    vm_service.suspend()
    assert assert_utils.equals_within_long(lambda: vm_service.get().status, types.VmStatus.SUSPENDED)

    vm_service.start()


@order_by(_TEST_LIST)
def test_verify_suspend_resume_vm0(engine_api, vm_ssh, vm0_fqdn_or_ip):
    _verify_vm_state(engine_api.system_service(), VM0_NAME, types.VmStatus.UP)
    ret = vm_ssh(vm0_fqdn_or_ip, 'pidof sleep')
    assert ret.code == EX_OK


@order_by(_TEST_LIST)
def test_reconstruct_master_domain(engine_api, ost_dc_name):
    pytest.skip('TODO:Handle case where tasks are running')
    system_service = engine_api.system_service()
    dc_service = test_utils.data_center_service(system_service, ost_dc_name)
    attached_sds_service = dc_service.storage_domains_service()
    master_sd = next(sd for sd in attached_sds_service.list() if sd.master)
    attached_sd_service = attached_sds_service.storage_domain_service(master_sd.id)
    attached_sd_service.deactivate()
    assert assert_utils.equals_within_long(
        lambda: attached_sd_service.get().status,
        types.StorageDomainStatus.MAINTENANCE,
    )
    new_master_sd = next(sd for sd in attached_sds_service.list() if sd.master)
    assert new_master_sd.id != master_sd.id
    attached_sd_service.activate()
    assert assert_utils.equals_within_long(
        lambda: attached_sd_service.get().status,
        types.StorageDomainStatus.ACTIVE,
    )


@order_by(_TEST_LIST)
def test_ovf_import(root_dir, engine_api, ost_cluster_name):
    # Read the OVF file and replace the disk id
    engine = engine_api.system_service()
    disk_service = test_utils.get_disk_service(engine, DISK0_NAME)
    disk_id = disk_service.get().id
    ovf_file = os.path.join(root_dir, 'common/test-scenarios-files/test-vm.ovf')
    ovf_text = open(ovf_file).read()
    ovf_text = ovf_text.replace(
        "ovf:diskId='52df5324-2230-40d9-9d3d-8cbb2aa33ba6'",
        "ovf:diskId='%s'" % (disk_id,),
    )
    # Upload OVF
    vms_service = engine.vms_service()
    vms_service.add(
        types.Vm(
            name=OVF_VM_NAME,
            cluster=types.Cluster(
                name=ost_cluster_name,
            ),
            initialization=types.Initialization(
                configuration=types.Configuration(type=types.ConfigurationType.OVA, data=ovf_text)
            ),
        )
    )
    # Check the VM exists
    assert test_utils.get_vm_service(engine, OVF_VM_NAME) is not None
