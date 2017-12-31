# -*- coding: utf-8 -*-
#
# Copyright 2014, 2017 Red Hat, Inc.
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
from os import EX_OK
import re
import nose.tools as nt
from nose import SkipTest

from ovirtsdk.xml import params

from lago import utils, ssh
from ovirtlago import testlib

import ovirtsdk4.types as types

import time

import test_utils


MB = 2 ** 20
GB = 2 ** 30
# the default MAC pool has addresses like 00:1a:4a:16:01:51
UNICAST_MAC_OUTSIDE_POOL = '0a:1a:4a:16:01:51'

TEST_DC = 'test-dc'
TEST_CLUSTER = 'test-cluster'
TEMPLATE_BLANK = 'Blank'
TEMPLATE_CENTOS7 = 'centos7_template'
TEMPLATE_CIRROS = 'CirrOS_0.3.5_for_x86_64_glance_template'

SD_NFS_NAME = 'nfs'
SD_SECOND_NFS_NAME = 'second-nfs'
SD_ISCSI_NAME = 'iscsi'

VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
VM2_NAME = 'vm2'
IMPORTED_VM_NAME = 'imported_vm'
VM0_PING_DEST = VM0_NAME
VMPOOL_NAME = 'test-pool'
DISK0_NAME = '%s_disk0' % VM0_NAME
DISK1_NAME = '%s_disk1' % VM1_NAME
DISK2_NAME = '%s_disk2' % VM2_NAME
GLANCE_DISK_NAME = 'CirrOS_0.3.5_for_x86_64_glance_disk'

SD_ISCSI_HOST_NAME = testlib.get_prefixed_name('engine')
SD_ISCSI_TARGET = 'iqn.2014-07.org.ovirt:storage'
SD_ISCSI_PORT = 3260
SD_ISCSI_NR_LUNS = 2
DLUN_DISK_NAME = 'DirectLunDisk'
SD_TEMPLATES_NAME = 'templates'

VM_NETWORK = u'VM Network with a very long name and עברית'
NETWORK_FILTER_NAME = 'clean-traffic'
NETWORK_FILTER_PARAMETER0_NAME = 'CTRL_IP_LEARNING'
NETWORK_FILTER_PARAMETER0_VALUE = 'dhcp'
NETWORK_FILTER_PARAMETER1_NAME = 'DHCPSERVER'

SNAPSHOT_DESC_1 = 'dead_snap1'
SNAPSHOT_DESC_2 = 'dead_snap2'


def _ping(ovirt_prefix, destination):
    """
    Ping a given destination.
    """
    host = ovirt_prefix.virt_env.host_vms()[0]
    cmd = ['ping', '-4', '-c', '1']
    ret = host.ssh(cmd + [destination])
    return ret.code


def _vm_host(prefix, vm_name):
    engine = prefix.virt_env.engine_vm().get_api_v4().system_service()
    vm_service = test_utils.get_vm_service(engine, vm_name)
    host_id = vm_service.get().host.id
    host_name = engine.hosts_service().host_service(host_id).get().name
    return prefix.virt_env.get_vm(host_name)


@testlib.with_ovirt_api
def add_blank_vms(api):
    vm_memory = 256 * MB
    vm_params = params.VM(
        memory=vm_memory,
        os=params.OperatingSystem(
            type_='other_linux',
        ),
        type_='server',
        high_availability=params.HighAvailability(
            enabled=False,
        ),
        cluster=params.Cluster(
            name=TEST_CLUSTER,
        ),
        template=params.Template(
            name=TEMPLATE_BLANK,
        ),
        display=params.Display(
            smartcard_enabled=True,
            keyboard_layout='en-us',
            file_transfer_enabled=True,
            copy_paste_enabled=True,
        ),
        memory_policy=params.MemoryPolicy(
            guaranteed=vm_memory / 2,
        ),
        name=VM0_NAME
    )
    api.vms.add(vm_params)
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'down',
    )
    vm_params.name = VM2_NAME
    vm_params.high_availability.enabled = True
    api.vms.add(vm_params)
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM2_NAME).status.state == 'down',
    )



@testlib.with_ovirt_api
def add_nic(api):
    NIC_NAME = 'eth0'
    nic_params = params.NIC(
        name=NIC_NAME,
        interface='virtio',
        network=params.Network(
            name='ovirtmgmt',
        ),
    )
    api.vms.get(VM0_NAME).nics.add(nic_params)

    nic_params.mac = params.MAC(address=UNICAST_MAC_OUTSIDE_POOL)
    nic_params.interface='e1000'
    api.vms.get(VM2_NAME).nics.add(nic_params)


@testlib.with_ovirt_api4
def add_disks(api):
    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    glance_disk = test_utils.get_disk_service(engine, GLANCE_DISK_NAME)
    nt.assert_true(vm_service and glance_disk)

    disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM0_NAME)

    disk_attachments_service.add(
        types.DiskAttachment(
            disk=types.Disk(
                id=glance_disk.get().id,
                storage_domains=[
                    types.StorageDomain(
                        name=SD_ISCSI_NAME,
                    ),
                ],
            ),
            interface=types.DiskInterface.VIRTIO,
            active=True,
            bootable=True,
        ),
    )

    disk_params = types.Disk(
        provisioned_size=1 * GB,
        format=types.DiskFormat.COW,
        status=None,
        sparse=True,
        active=True,
        bootable=True,
    )

    for vm_name, disk_name, sd_name in (
            (VM1_NAME, DISK1_NAME, SD_NFS_NAME),
            (VM2_NAME, DISK2_NAME, SD_SECOND_NFS_NAME)):
        disk_params.name = disk_name
        disk_params.storage_domains = [
            types.StorageDomain(
                name=sd_name,
            )
        ]

        disk_attachments_service = test_utils.get_disk_attachments_service(engine, vm_name)
        nt.assert_true(
            disk_attachments_service.add(types.DiskAttachment(
                disk=disk_params,
                interface=types.DiskInterface.VIRTIO))
        )

    for disk_name in (GLANCE_DISK_NAME, DISK1_NAME, DISK2_NAME):
        disk_service = test_utils.get_disk_service(engine, disk_name)
        testlib.assert_true_within_short(
            lambda:
            disk_service.get().status == types.DiskStatus.OK
        )


@testlib.with_ovirt_api4
def extend_disk1(api):
    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM1_NAME)
    disk_attachments_service = vm_service.disk_attachments_service()
    for disk_attachment in disk_attachments_service.list():
        disk = api.follow_link(disk_attachment.disk)
        if disk.name == DISK1_NAME:
            attachment_service = disk_attachments_service.attachment_service(disk_attachment.id)
            attachment_service.update(
                    types.DiskAttachment(
                        disk=types.Disk(provisioned_size=2 * GB,)))

    disk_service = test_utils.get_disk_service(engine, DISK1_NAME)
    testlib.assert_true_within_short(
        lambda:
        disk_service.get().status == types.DiskStatus.OK and \
        disk_service.get().provisioned_size == 2 * GB
    )


@testlib.with_ovirt_api4
def sparsify_disk1(api):
    engine = api.system_service()
    disk_service = test_utils.get_disk_service(engine, DISK1_NAME)
    disk_service.sparsify()
    testlib.assert_true_within_short(
        lambda:
        disk_service.get().status == types.DiskStatus.OK
    )


@testlib.with_ovirt_api
def add_graphics_console(api):
    vm = api.vms.get(VM0_NAME)
    vm.graphicsconsoles.add(
        params.GraphicsConsole(
            protocol='vnc',
        )
    )
    testlib.assert_true_within_short(
        lambda:
        len(api.vms.get(VM0_NAME).graphicsconsoles.list()) == 2
    )


@testlib.with_ovirt_prefix
def add_directlun(prefix):
    # Find LUN GUIDs
    iscsi_host = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME)
    ret = iscsi_host.ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)

    all_guids = ret.out.splitlines()
    lun_guid = all_guids[SD_ISCSI_NR_LUNS]  # Take the first unused LUN. 0-(SD_ISCSI_NR_LUNS) are used by iSCSI SD

    ips = iscsi_host.all_ips()
    luns = []
    for ip in ips:
        lun=types.LogicalUnit(
                id=lun_guid,
                address=ip,
                port=SD_ISCSI_PORT,
                target=SD_ISCSI_TARGET,
                username='username',
                password='password',
            )
        luns.append(lun)

    dlun_params = types.Disk(
        name=DLUN_DISK_NAME,
        format=types.DiskFormat.RAW,
        lun_storage=types.HostStorage(
            type=types.StorageType.ISCSI,
            logical_units=luns,
        ),
        sgio=types.ScsiGenericIO.UNFILTERED,
    )

    api = prefix.virt_env.engine_vm().get_api_v4()
    engine = api.system_service()
    disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM0_NAME)
    disk_attachments_service.add(types.DiskAttachment(
        disk=dlun_params,
        interface=types.DiskInterface.VIRTIO_SCSI))

    disk_service = test_utils.get_disk_service(engine, DLUN_DISK_NAME)
    attachment_service = disk_attachments_service.attachment_service(disk_service.get().id)
    nt.assert_not_equal(
        attachment_service.get(),
        None,
        'Direct LUN disk not attached'
    )


@testlib.with_ovirt_api4
def snapshot_cold_merge(api):
    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM1_NAME)

    if vm_service is None:
        raise SkipTest('Glance is not available')

    snapshots_service = vm_service.snapshots_service()
    disk = engine.disks_service().list(search=DISK1_NAME)[0]

    dead_snap1_params = types.Snapshot(
        description=SNAPSHOT_DESC_1,
        persist_memorystate=False,
        disk_attachments=[
            types.DiskAttachment(
                disk=types.Disk(
                    id=disk.id
                )
            )
        ]
    )

    snapshots_service.add(dead_snap1_params)

    testlib.assert_true_within_long(
        lambda:
        snapshots_service.list()[-1].snapshot_status == types.SnapshotStatus.OK
    )

    dead_snap2_params = types.Snapshot(
        description=SNAPSHOT_DESC_2,
        persist_memorystate=False,
        disk_attachments=[
            types.DiskAttachment(
                disk=types.Disk(
                    id=disk.id
                )
            )
        ]
    )

    snapshots_service.add(dead_snap2_params)

    testlib.assert_true_within_long(
        lambda:
        snapshots_service.list()[-1].snapshot_status == types.SnapshotStatus.OK
    )

    snapshot = snapshots_service.list()[-2]
    snapshots_service.snapshot_service(snapshot.id).remove()

    testlib.assert_true_within_long(
        lambda:
        (len(snapshots_service.list()) == 2) and
        (
            snapshots_service.list()[-1].snapshot_status == (
                types.SnapshotStatus.OK
            )
        ),
    )


@testlib.with_ovirt_api4
def cold_storage_migration(api):
    disk_service = test_utils.get_disk_service(api.system_service(), DISK2_NAME)

    # Cold migrate the disk to ISCSI storage domain and then migrate it back
    # to the NFS domain because it is used by other cases that assume the
    # disk found on that specific domain
    for domain in [SD_ISCSI_NAME, SD_SECOND_NFS_NAME]:
        disk_service.move(
            async=False,
            storage_domain=types.StorageDomain(
                name=domain
            )
        )

        testlib.assert_true_within_long(
            lambda: api.follow_link(
                disk_service.get().storage_domains[0]
            ).name == domain and (
                disk_service.get().status == types.DiskStatus.OK
            )
        )


@testlib.with_ovirt_api4
def live_storage_migration(api):
    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    disk_service = test_utils.get_disk_service(engine, DISK0_NAME)
    disk_service.move(
        async=False,
        filter=False,
        storage_domain=types.StorageDomain(
            name=SD_ISCSI_NAME
        )
    )

    snapshots_service = vm_service.snapshots_service()
    # Assert that the disk is on the correct storage domain,
    # its status is OK and the snapshot created for the migration
    # has been merged
    testlib.assert_equals_within_long(
        lambda: api.follow_link(disk_service.get().storage_domains[0]).name == SD_ISCSI_NAME and \
                len(snapshots_service.list()) == 1 and \
                disk_service.get().status, types.DiskStatus.OK)

    # This sleep is a temporary solution to the race condition
    # https://bugzilla.redhat.com/1456504
    time.sleep(3)


@testlib.with_ovirt_api4
def export_vm1(api):
    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM1_NAME)
    sd = engine.storage_domains_service().list(search=SD_TEMPLATES_NAME)[0]

    vm_service.export(
        storage_domain=types.StorageDomain(
            id=sd.id,
        ), discard_snapshots=True, async=True
    )


@testlib.with_ovirt_api4
def verify_vm1_exported(api):
    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM1_NAME)
    testlib.assert_true_within_short(
        lambda:
        vm_service.get().status == types.VmStatus.DOWN
    )

    storage_domain_service = test_utils.get_storage_domain_service(engine, SD_TEMPLATES_NAME)
    vm_sd_service = test_utils.get_storage_domain_vm_service_by_name(
        storage_domain_service, VM1_NAME)
    testlib.assert_true_within_short(
        lambda:
        vm_sd_service.get().status == types.VmStatus.DOWN
    )


@testlib.with_ovirt_api4
def import_vm_as_clone(api):
    engine = api.system_service()
    storage_domain_service = test_utils.get_storage_domain_service(engine, SD_TEMPLATES_NAME)
    vm_to_import = test_utils.get_storage_domain_vm_service_by_name(storage_domain_service, VM1_NAME)

    if vm_to_import is None:
        raise SkipTest("VM: '%s' not found on export domain: '%s'" % (VM1_NAME, SD_TEMPLATES_NAME))

    vm_to_import.import_(
        storage_domain=types.StorageDomain(
            name=SD_ISCSI_NAME,
        ),
        cluster=types.Cluster(
            name=TEST_CLUSTER,
        ),
        vm=types.Vm(
            name=IMPORTED_VM_NAME,
        ),
        clone=True, collapse_snapshots=True, async=True
    )


@testlib.with_ovirt_api4
def verify_vm_import(api):
    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, IMPORTED_VM_NAME)
    testlib.assert_true_within_short(
        lambda: vm_service.get().status == types.VmStatus.DOWN
    )

    # Remove the imported VM
    num_of_vms = len(engine.vms_service().list())
    vm_service.remove()
    nt.assert_true(len(engine.vms_service().list()) == (num_of_vms-1))


@testlib.with_ovirt_api
def add_vm1_from_template(api):
    #TODO: Fix the exported domain generation.
    #For the time being, add VM from Glance imported template.
    if api.templates.get(name=TEMPLATE_CIRROS) is None:
        raise SkipTest('%s: template %s not available.' % (add_vm1_from_template.__name__, TEMPLATE_CIRROS))

    vm_memory = 512 * MB
    vm_params = params.VM(
        name=VM1_NAME,
        description='CirrOS imported from Glance as Template',
        memory=vm_memory,
        cluster=params.Cluster(
            name=TEST_CLUSTER,
        ),
        template=params.Template(
            name=TEMPLATE_CIRROS,
        ),
        use_latest_template_version=True,
        stateless=True,
        display=params.Display(
            type_='vnc',
        ),
        memory_policy=params.MemoryPolicy(
            guaranteed=vm_memory / 2,
            ballooning=False,
        ),
        os=params.OperatingSystem(
            type_='other_linux',
        ),
        timezone='Etc/GMT',
        type_='server',
        serial_number=params.SerialNumber(
            policy='custom',
            value='12345678',
        ),
        cpu=params.CPU(
            architecture='X86_64',
            topology=params.CpuTopology(
                cores=1,
                threads=2,
                sockets=1,
            ),
        ),
    )
    api.vms.add(vm_params)


@testlib.with_ovirt_api
def verify_add_vm1_from_template(api):
    vm = api.vms.get(VM1_NAME)
    nt.assert_true(vm)

    testlib.assert_true_within_long(
        lambda: api.vms.get(VM1_NAME).status.state == 'down',
    )
    disk_name = vm.disks.list()[0].name
    testlib.assert_true_within_long(
        lambda:
        vm.disks.get(disk_name).status.state == 'ok'
    )


@testlib.with_ovirt_api4
def add_filter(ovirt_api4):
    engine = ovirt_api4.system_service()
    nics_service = test_utils.get_nics_service(engine, VM0_NAME)
    nic = nics_service.list()[0]
    network = ovirt_api4.follow_link(nic.vnic_profile).network
    network_filters_service = engine.network_filters_service()
    network_filter = next(
        network_filter for network_filter in network_filters_service.list()
        if network_filter.name == NETWORK_FILTER_NAME
    )
    vnic_profiles_service = engine.vnic_profiles_service()

    vnic_profile = vnic_profiles_service.add(
        types.VnicProfile(
            name='{}_profile'.format(network_filter.name),
            network=network,
            network_filter=network_filter
        )
    )
    nic.vnic_profile = vnic_profile
    nt.assert_true(
        nics_service.nic_service(nic.id).update(nic)
    )


@testlib.with_ovirt_prefix
def add_filter_parameter(prefix):
    engine = prefix.virt_env.engine_vm()
    ovirt_api4 = engine.get_api(api_ver=4)
    vm_gw = '.'.join(engine.ip().split('.')[0:3] + ['1'])
    network_filter_parameters_service = test_utils.get_network_fiter_parameters_service(
        ovirt_api4.system_service(), VM0_NAME)

    nt.assert_true(
        network_filter_parameters_service.add(
            types.NetworkFilterParameter(
                name=NETWORK_FILTER_PARAMETER0_NAME,
                value=NETWORK_FILTER_PARAMETER0_VALUE
            )
        )
    )

    nt.assert_true(
        network_filter_parameters_service.add(
            types.NetworkFilterParameter(
                name=NETWORK_FILTER_PARAMETER1_NAME,
                value=vm_gw
            )
        )
    )

@testlib.with_ovirt_prefix
def run_vms(prefix):
    engine = prefix.virt_env.engine_vm()
    api = engine.get_api()
    vm_ip = '.'.join(engine.ip().split('.')[0:3] + ['199'])
    vm_gw = '.'.join(engine.ip().split('.')[0:3] + ['1'])
    host_names = [h.name() for h in prefix.virt_env.host_vms()]

    start_params = params.Action(
        use_cloud_init=True,
        vm=params.VM(
            placement_policy=params.VmPlacementPolicy(
                host=params.Host(
                    name=sorted(host_names)[0]
                ),
            ),
            initialization=params.Initialization(
                domain=params.Domain(
                    name='lago.example.com'
                ),
                cloud_init=params.CloudInit(
                    host=params.Host(
                        address='VM0'
                    ),
                    users=params.Users(
                        active=True,
                        user=[params.User(
                            user_name='root',
                            password='secret'
                        )]
                    ),
                    network_configuration=params.NetworkConfiguration(
                        nics=params.Nics(
                            nic=[params.NIC(
                                name='eth0',
                                boot_protocol='STATIC',
                                on_boot=True,
                                network=params.Network(
                                    ip=params.IP(
                                        address=vm_ip,
                                        netmask='255.255.255.0',
                                        gateway=vm_gw,
                                    ),
                                ),
                            )]
                        ),
                    ),
                ),
            ),
        ),
    )
    api.vms.get(VM0_NAME).start(start_params)
    start_params.vm.initialization.cloud_init=params.CloudInit(
        host=params.Host(
            address='VM2'
        ),
    )
    api.vms.get(VM2_NAME).start(start_params)

    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'up',
    )


@testlib.with_ovirt_api
def verify_vm2_run(api):
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM2_NAME).status.state == 'up',
    )


@testlib.with_ovirt_prefix
def ping_vm0(ovirt_prefix):
    nt.assert_equals(_ping(ovirt_prefix, VM0_PING_DEST), EX_OK)


@testlib.with_ovirt_prefix
def restore_vm0_networking(ovirt_prefix):
    # Networking may not work after resume.  We need this pseudo-test for the
    # purpose of reviving VM networking by rebooting the VM.  We must be
    # careful to reboot just the guest OS, not to restart the whole VM, to keep
    # checking for contingent failures after resume.
    # A better solution might be using a guest OS other than Cirros.
    if _ping(ovirt_prefix, VM0_PING_DEST) == EX_OK:
        return
    host = _vm_host(ovirt_prefix, VM0_NAME)
    uri = 'qemu+tls://%s/system' % host.name()
    ret = host.ssh(['virsh', '-c', uri, 'reboot', '--mode', 'acpi', VM0_NAME])
    nt.assert_equals(ret.code, EX_OK)
    testlib.assert_true_within_long(
        lambda:
        _ping(ovirt_prefix, VM0_PING_DEST) == EX_OK
    )

    engine = ovirt_prefix.virt_env.engine_vm().get_api_v4().system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    testlib.assert_true_within_long(
        lambda:
        vm_service.get().status == types.VmStatus.UP
    )


@testlib.with_ovirt_prefix
def ha_recovery(prefix):
    engine = prefix.virt_env.engine_vm().get_api_v4().system_service()
    last_event = int(engine.events_service().list(max=2)[0].id)
    vm_host = _vm_host(prefix, VM2_NAME)
    pid = vm_host.ssh(['pgrep', '-f', 'qemu.*guest=vm2'])
    vm_host.ssh(['kill', '-KILL', pid.out])
    events = engine.events_service()
    testlib.assert_true_within_short(
        lambda:
        (next(e for e in events.list(from_=last_event) if e.code == 9602)).code == 9602,
         allowed_exceptions=[StopIteration]
    )
    vm_service = test_utils.get_vm_service(engine, VM2_NAME)
    testlib.assert_true_within_long(
        lambda:
        vm_service.get().status == types.VmStatus.UP
    )
    vm_service.stop()


@testlib.with_ovirt_prefix
def vdsm_recovery(prefix):
    engine = prefix.virt_env.engine_vm().get_api_v4().system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    host_id = vm_service.get().host.id
    host_service = engine.hosts_service().host_service(host_id)
    host_name = host_service.get().name
    vm_host = prefix.virt_env.get_vm(host_name)

    vm_host.service('vdsmd').stop()
    testlib.assert_true_within_short(
        lambda:
        vm_service.get().status == types.VmStatus.UNKNOWN
    )

    vm_host.service('vdsmd').start()
    testlib.assert_true_within_short(
        lambda:
        host_service.get().status == types.HostStatus.UP
    )
    testlib.assert_true_within_short(
        lambda:
        vm_service.get().status == types.VmStatus.UP
    )


@testlib.with_ovirt_api4
def template_export(api):
    engine = api.system_service()

    template_cirros = test_utils.get_template_service(engine, TEMPLATE_CIRROS)
    if template_cirros is None:
        raise SkipTest('{0}: template {1} is missing'.format(
            template_export.__name__,
            TEMPLATE_CIRROS
            )
        )

    storage_domain = engine.storage_domains_service().list(search=SD_TEMPLATES_NAME)[0]
    template_cirros.export(
        storage_domain=types.StorageDomain(
            id=storage_domain.id,
        ),
    )
    testlib.assert_true_within_long(
        lambda:
        template_cirros.get().status == types.TemplateStatus.OK,
    )


@testlib.with_ovirt_api4
def add_vm_pool(api):
    engine = api.system_service()
    pools_service = engine.vm_pools_service()
    pool_cluster = engine.clusters_service().list(search=TEST_CLUSTER)[0]
    pool_template = engine.templates_service().list(search=TEMPLATE_CIRROS)[0]
    pools_service.add(
        pool=types.VmPool(
            name=VMPOOL_NAME,
            cluster=pool_cluster,
            template=pool_template,
            use_latest_template_version=True,
        )
    )
    vm_service = test_utils.get_vm_service(engine, VMPOOL_NAME+'-1')
    testlib.assert_true_within_short(
        lambda:
        vm_service.get().status == types.VmStatus.DOWN,
        allowed_exceptions=[IndexError]
    )


@testlib.with_ovirt_api4
def update_template_version(api):
    engine = api.system_service()
    stateless_vm = engine.vms_service().list(search=VM1_NAME)[0]
    templates_service = engine.templates_service()
    template = templates_service.list(search=TEMPLATE_CIRROS)[0]

    nt.assert_true(stateless_vm.memory != template.memory)

    templates_service.add(
        template=types.Template(
            name=TEMPLATE_CIRROS,
            vm=stateless_vm,
            version=types.TemplateVersion(
                base_template=template,
                version_number=2
            )
        )
    )
    pool_service = test_utils.get_pool_service(engine, VMPOOL_NAME)
    testlib.assert_true_within_long(
        lambda:
        pool_service.get().vm.memory == stateless_vm.memory
    )


@testlib.with_ovirt_api4
def update_vm_pool(api):
    pool_service = test_utils.get_pool_service(api.system_service(), VMPOOL_NAME)
    pool_service.update(
        pool=types.VmPool(
            max_user_vms=2
        )
    )
    nt.assert_true(
        pool_service.get().max_user_vms == 2
    )


@testlib.with_ovirt_api4
def remove_vm_pool(api):
    pool_service = test_utils.get_pool_service(api.system_service(), VMPOOL_NAME)
    pool_service.remove()
    vm_pools_service = api.system_service().vm_pools_service()
    nt.assert_true(
         len(vm_pools_service.list()) == 0
    )


@testlib.with_ovirt_api4
def template_update(api):
    template_cirros = test_utils.get_template_service(api.system_service(), TEMPLATE_CIRROS)

    if template_cirros is None:
        raise SkipTest('{0}: template {1} is missing'.format(
            template_update.__name__,
            TEMPLATE_CIRROS
        )
    )
    new_comment = "comment by ovirt-system-tests"
    template_cirros.update(
        template = types.Template(
            comment=new_comment
        )
    )
    testlib.assert_true_within_short(
        lambda:
        template_cirros.get().status == types.TemplateStatus.OK
    )
    nt.assert_true(
        template_cirros.get().comment == new_comment
    )


@testlib.with_ovirt_api4
def disk_operations(api):
    vt = utils.VectorThread(
        [
            functools.partial(live_storage_migration),
            functools.partial(cold_storage_migration),
            functools.partial(snapshot_cold_merge),
        ],
    )
    vt.start_all()
    vt.join_all()


@testlib.with_ovirt_api4
def hotplug_memory(api):
    vm_service = test_utils.get_vm_service(api.system_service(), VM0_NAME)
    new_memory = vm_service.get().memory * 2
    vm_service.update(
        vm=types.Vm(
            memory=new_memory
        )
    )
    nt.assert_true(
        vm_service.get().memory == new_memory
    )


@testlib.with_ovirt_prefix
def hotplug_cpu(prefix):
    api = prefix.virt_env.engine_vm().get_api_v4()
    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM0_NAME)
    new_cpu = vm_service.get().cpu
    new_cpu.topology.sockets = 2
    vm_service.update(
        vm=types.Vm(
            cpu=new_cpu
        )
    )
    nt.assert_true(
        vm_service.get().cpu.topology.sockets == 2
    )

    host = prefix.virt_env.host_vms()[0]
    ret = host.ssh(['host', VM0_NAME])
    match = re.search(r'\s([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', ret.out)
    ip_address = match.group(1)
    ret = ssh.ssh(
        ip_addr=ip_address,
        command=['lscpu'],
        username='cirros',
        password='cubswin:)',
    )
    nt.assert_equals(ret.code, 0)
    match = re.search(r'CPU\(s\):\s+(?P<cpus>[0-9]+)', ret.out)
    nt.assert_true(match.group('cpus') == '2')


@testlib.with_ovirt_api4
def next_run_unplug_cpu(api):
    vm_service = test_utils.get_vm_service(api.system_service(), VM0_NAME)
    new_cpu = vm_service.get().cpu
    new_cpu.topology.sockets = 1
    vm_service.update(
        vm=types.Vm(
            cpu=new_cpu,
        ),
        next_run=True
    )
    nt.assert_true(
        vm_service.get().cpu.topology.sockets == 2
    )
    nt.assert_true(
        vm_service.get(next_run=True).cpu.topology.sockets == 1
    )
    vm_service.reboot()
    testlib.assert_true_within_long(
        lambda:
         vm_service.get().status == types.VmStatus.UP
    )
    nt.assert_true(
        vm_service.get().cpu.topology.sockets == 1
    )


@testlib.with_ovirt_api
def hotplug_nic(api):
    nic2_params = params.NIC(
        name='eth1',
        network=params.Network(
            name=VM_NETWORK,
        ),
        interface='virtio',
    )
    api.vms.get(VM0_NAME).nics.add(nic2_params)


@testlib.with_ovirt_api4
def hotplug_disk(api):
    disk_attachments_service = test_utils.get_disk_attachments_service(api.system_service(), VM0_NAME)
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
            interface=types.DiskInterface.VIRTIO,
            bootable=False,
            active=True
        )
    )

    disks_service = api.system_service().disks_service()
    disk_service = disks_service.disk_service(disk_attachment.disk.id)
    attachment_service = disk_attachments_service.attachment_service(disk_attachment.id)

    testlib.assert_true_within_short(
        lambda:
        attachment_service.get().active and
        disk_service.get().status == types.DiskStatus.OK
    )


@testlib.with_ovirt_api4
def hotunplug_disk(api):
    engine = api.system_service()
    disk_service = test_utils.get_disk_service(engine, DISK0_NAME)
    disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM0_NAME)
    disk_attachment = disk_attachments_service.attachment_service(disk_service.get().id)

    nt.assert_true(
        disk_attachment.update(types.DiskAttachment(active=False))
    )

    testlib.assert_true_within_short(
        lambda:
        disk_attachment.get().active == False
    )


@testlib.with_ovirt_api
def suspend_resume_vm0(api):
    nt.assert_true(api.vms.get(VM0_NAME).suspend())

    testlib.assert_true_within_long(
        lambda:
        api.vms.get(VM0_NAME).status.state == 'suspended'
    )

    nt.assert_true(api.vms.get(VM0_NAME).start())


@testlib.with_ovirt_api
def verify_suspend_resume_vm0(api):
    testlib.assert_true_within_long(
        lambda:
        api.vms.get(VM0_NAME).status.state == 'up'
    )


@testlib.with_ovirt_api
def add_event(api):
    event_params = params.Event(
        description='ovirt-system-tests description',
        custom_id=int('01234567890'),
        severity='NORMAL',
        origin='ovirt-system-tests',
        cluster=params.Cluster(
            name=TEST_CLUSTER,
        ),
    )

    nt.assert_true(api.events.add(event_params))


@testlib.with_ovirt_api4
def add_instance_type(api):
    instance_types_service = api.system_service().instance_types_service()
    nt.assert_true(
        instance_types_service.add(
            types.InstanceType(
                name='myinstancetype',
                description='My instance type',
                memory=1 * 2**30,
                memory_policy=types.MemoryPolicy(
                    max=1 * 2**30,
                ),
                high_availability=types.HighAvailability(
                    enabled=True,
                ),
                cpu=types.Cpu(
                    topology=types.CpuTopology(
                        cores=2,
                        sockets=2,
                    ),
                ),
            ),
        )
    )


@testlib.with_ovirt_api
def verify_glance_import(api):
    for disk_name in (GLANCE_DISK_NAME, TEMPLATE_CIRROS):
        testlib.assert_true_within_long(
            lambda: api.disks.get(disk_name).status.state == 'ok',
        )


@testlib.with_ovirt_api4
def add_serial_console_vm2(api):
    engine = api.system_service()
    # Find the virtual machine. Note the use of the `all_content` parameter, it is
    # required in order to obtain additional information that isn't retrieved by
    # default, like the configuration of the serial console.
    vm = engine.vms_service().list(search=VM2_NAME, all_content=True)[0]
    if not vm.console.enabled:
        vm_service = test_utils.get_vm_service(engine, VM2_NAME)
        vm_service.update(
            types.Vm(
                console=types.Console(
                    enabled=True
                )
            )
        )


_TEST_LIST = [
    add_blank_vms,
    verify_glance_import,
    add_vm1_from_template,
    add_nic,
    add_graphics_console,
    add_directlun,
    add_filter,
    add_filter_parameter,
    add_serial_console_vm2,
    verify_add_vm1_from_template,
    add_disks,
    run_vms,
    ping_vm0,
    suspend_resume_vm0,
    extend_disk1,
    sparsify_disk1,
    export_vm1,
    verify_vm2_run,
    ha_recovery,
    verify_vm1_exported,
    import_vm_as_clone,
    template_export,
    template_update,
    add_instance_type,
    add_event,
    verify_vm_import,
    verify_suspend_resume_vm0,
    restore_vm0_networking,
    hotplug_memory,
    hotplug_disk,
    hotplug_nic,
    hotplug_cpu,
    next_run_unplug_cpu,
    disk_operations,
    hotunplug_disk,
    add_vm_pool,
    update_template_version,
    update_vm_pool,
    remove_vm_pool,
    vdsm_recovery
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
