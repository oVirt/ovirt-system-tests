#
# Copyright 2014 Red Hat, Inc.
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
import nose.tools as nt
from nose import SkipTest

from ovirtsdk.xml import params

from lago import utils
from ovirtlago import testlib

import ovirtsdk4
import ovirtsdk4.types as types

import time

MB = 2 ** 20
GB = 2 ** 30
# the default MAC pool has addresses like 00:1a:4a:16:01:51
UNICAST_MAC_OUTSIDE_POOL = '0a:1a:4a:16:01:51'

TEST_DC = 'test-dc'
TEST_CLUSTER = 'test-cluster'
TEMPLATE_BLANK = 'Blank'
TEMPLATE_CENTOS7 = 'centos7_template'
TEMPLATE_CIRROS = 'CirrOS_0.3.4_for_x86_64_glance_template'

SD_NFS_NAME = 'nfs'
SD_SECOND_NFS_NAME = 'second-nfs'
SD_ISCSI_NAME = 'iscsi'

VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
VM2_NAME = 'vm2'
DISK0_NAME = '%s_disk0' % VM0_NAME
DISK1_NAME = '%s_disk1' % VM1_NAME
DISK2_NAME = '%s_disk2' % VM2_NAME
GLANCE_DISK_NAME = 'CirrOS_0.3.4_for_x86_64_glance_disk'

SD_ISCSI_HOST_NAME = testlib.get_prefixed_name('engine')
SD_ISCSI_TARGET = 'iqn.2014-07.org.ovirt:storage'
SD_ISCSI_PORT = 3260
SD_ISCSI_NR_LUNS = 2
DLUN_DISK_NAME = 'DirectLunDisk'
SD_TEMPLATES_NAME = 'templates'

@testlib.with_ovirt_api
def add_vm_blank(api):
    vm_memory = 512 * MB
    vm_params = params.VM(
        memory=vm_memory,
        os=params.OperatingSystem(
            type_='other_linux',
        ),
        type_='server',
        high_availability=params.HighAvailability(
            enabled=True,
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
    )

    for vm_name in (VM0_NAME, VM2_NAME):
        vm_params.name = vm_name
        api.vms.add(vm_params)
        testlib.assert_true_within_short(
            lambda: api.vms.get(vm_name).status.state == 'down',
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
    api.vms.get(VM2_NAME).nics.add(nic_params)


@testlib.with_ovirt_api
def add_disk(api):
    glance_disk = api.disks.get(GLANCE_DISK_NAME)
    if glance_disk:
        nt.assert_true(
            api.vms.get(VM0_NAME).disks.add(
                params.Disk(
                    id = glance_disk.get_id(),
                    active=True,
                    bootable=True,
                )
            )
        )

    disk_params = params.Disk(
        size=10 * GB,
        provisioned_size=1,
        interface='virtio',
        format='cow',
        status=None,
        sparse=True,
        active=True,
        bootable=True,
    )

    for vm_name, disk_name, sd_name in (
            (VM1_NAME, DISK1_NAME, SD_NFS_NAME),
            (VM2_NAME, DISK2_NAME, SD_SECOND_NFS_NAME)):
        if api.vms.get(vm_name) is not None:
            disk_params.name = disk_name
            disk_params.storage_domains = params.StorageDomains(
                storage_domain=[
                    params.StorageDomain(
                        name=sd_name,
                    ),
                ])
            nt.assert_true(
                api.vms.get(vm_name).disks.add(disk_params)
            )

    if glance_disk:
        testlib.assert_true_within_short(
            lambda:
            api.vms.get(VM0_NAME).disks.get(GLANCE_DISK_NAME).status.state == 'ok'
        )
    for vm_name, disk_name in ((VM1_NAME, DISK1_NAME),
                               (VM2_NAME, DISK2_NAME)):
        if api.vms.get(vm_name) is not None:
            testlib.assert_true_within_short(
                lambda:
                api.vms.get(vm_name).disks.get(disk_name).status.state == 'ok'
            )


@testlib.with_ovirt_api
def add_console(api):
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
    ret = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)

    all_guids = ret.out.splitlines()
    lun_guid = all_guids[SD_ISCSI_NR_LUNS] #Take the first unused LUN. 0-(SD_ISCSI_NR_LUNS) are used by iSCSI SD

    dlun_params = params.Disk(
        name=DLUN_DISK_NAME,
        interface='virtio_scsi',
        format='raw',
        lun_storage=params.Storage(
            type_='iscsi',
            logical_unit=[
                params.LogicalUnit(
                    id=lun_guid,
                    address=prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ip(),
                    port=SD_ISCSI_PORT,
                    target=SD_ISCSI_TARGET,
                    username='username',
                    password='password',
                )
            ]
        ),
        sgio='unfiltered',
    )

    api = prefix.virt_env.engine_vm().get_api()
    api.vms.get(VM0_NAME).disks.add(dlun_params)
    nt.assert_not_equal(
        api.vms.get(VM0_NAME).disks.get(DLUN_DISK_NAME),
        None,
        'Direct LUN disk not attached'
    )


def snapshot_cold_merge(api):
    if api.vms.get(VM1_NAME) is None:
        raise SkipTest('Glance is not available')

    dead_snap1_params = params.Snapshot(
        description='dead_snap1',
        persist_memorystate=False,
        disks=params.Disks(
            disk=[
                params.Disk(
                    id=api.vms.get(VM1_NAME).disks.get(DISK1_NAME).id,
                ),
            ],
        ),
    )
    api.vms.get(VM1_NAME).snapshots.add(dead_snap1_params)
    testlib.assert_true_within_long(
        lambda:
        api.vms.get(VM1_NAME).snapshots.list()[-1].snapshot_status == 'ok'
    )

    dead_snap2_params = params.Snapshot(
        description='dead_snap2',
        persist_memorystate=False,
        disks=params.Disks(
            disk=[
                params.Disk(
                    id=api.vms.get(VM1_NAME).disks.get(DISK1_NAME).id,
                ),
            ],
        ),
    )
    api.vms.get(VM1_NAME).snapshots.add(dead_snap2_params)
    testlib.assert_true_within_long(
        lambda:
        api.vms.get(VM1_NAME).snapshots.list()[-1].snapshot_status == 'ok'
    )

    api.vms.get(VM1_NAME).snapshots.list()[-2].delete()
    testlib.assert_true_within_long(
        lambda:
        (len(api.vms.get(VM1_NAME).snapshots.list()) == 2) and
        (api.vms.get(VM1_NAME).snapshots.list()[-1].snapshot_status
         == 'ok'),
    )


@testlib.with_ovirt_api4
def live_storage_migration(api):
    engine = api.system_service()
    vms_service = engine.vms_service()
    vm = vms_service.list(search=VM0_NAME)[0]
    vm_service = vms_service.vm_service(vm.id)
    disks_service = engine.disks_service()
    disk = disks_service.list(search=DISK0_NAME)[0]
    disk_service = disks_service.disk_service(disk.id)
    disk_service.move(
        async=False,
        filter=False,
        storage_domain=types.StorageDomain(
            name=SD_ISCSI_NAME
        )
    )

    # Assert that the disk is on the correct storage domain,
    # its status is OK and the snapshot created for the migration
    # has been merged
    testlib.assert_equals_within_long(
        lambda: api.follow_link(disk_service.get().storage_domains[0]).name == SD_ISCSI_NAME and \
                len(vm_service.snapshots_service().list()) == 1 and \
                disk_service.get().status, types.DiskStatus.OK)

    # This sleep is a temporary solution to the race condition
    # https://bugzilla.redhat.com/1456504
    time.sleep(1)


@testlib.with_ovirt_api
def add_vm_template(api):
    #TODO: Fix the exported domain generation.
    #For the time being, add VM from Glance imported template.
    if api.templates.get(name=TEMPLATE_CIRROS) is None:
        raise SkipTest('%s: template %s not available.' % (add_vm_template.__name__, TEMPLATE_CIRROS))

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
    testlib.assert_true_within_long(
        lambda: api.vms.get(VM1_NAME).status.state == 'down',
    )
    disk_name = api.vms.get(VM1_NAME).disks.list()[0].name
    testlib.assert_true_within_long(
        lambda:
        api.vms.get(VM1_NAME).disks.get(disk_name).status.state == 'ok'
    )


@testlib.with_ovirt_prefix
def vm_run(prefix):
    api = prefix.virt_env.engine_vm().get_api()
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
                                on_boot='True',
                                network=params.Network(
                                    ip=params.IP(
                                        address='192.168.200.200.',
                                        netmask='255.255.255.0',
                                        gateway='192.168.200.1',
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
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'up',
    )


@testlib.with_ovirt_prefix
def vdsm_recovery(prefix):
    api = prefix.virt_env.engine_vm().get_api()
    host_id = api.vms.get(VM0_NAME).host.id
    vm_host_name = api.hosts.get(id=host_id).name
    hosts = prefix.virt_env.host_vms()
    vm_host = next(h for h in hosts if h.name() == vm_host_name)
    vm_host.service('vdsmd').stop()
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'unknown',
    )
    vm_host.service('vdsmd').start()
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'up',
    )


@testlib.with_ovirt_api
def template_export(api):
    template_cirros = api.templates.get(TEMPLATE_CIRROS)

    if template_cirros is None:
        raise SkipTest('{0}: template {1} is missing'.format(
            template_export.__name__,
            TEMPLATE_CIRROS
            )
        )

    template_cirros.export(
        params.Action(
            storage_domain=api.storagedomains.get(SD_TEMPLATES_NAME)
         )
    )
    testlib.assert_true_within_long(
        lambda: api.templates.get(TEMPLATE_CIRROS).status.state == 'ok',
    )


@testlib.with_ovirt_api
def disk_operations(api):
    vt= utils.VectorThread(
        [
            functools.partial(live_storage_migration),
            functools.partial(snapshot_cold_merge, api),
        ],
    )
    vt.start_all()
    vt.join_all()


@testlib.with_ovirt_api
def hotplug_nic(api):
    nic2_params = params.NIC(
        name='eth1',
        network=params.Network(
            name='ovirtmgmt',
        ),
        interface='virtio',
    )
    api.vms.get(VM0_NAME).nics.add(nic2_params)


@testlib.with_ovirt_api
def hotplug_disk(api):
    disk2_params = params.Disk(
        name=DISK0_NAME,
        size=9 * GB,
        provisioned_size=2,
        interface='virtio',
        format='cow',
        storage_domains=params.StorageDomains(
            storage_domain=[
                params.StorageDomain(
                    name=SD_NFS_NAME,
                ),
            ],
        ),
        status=None,
        sparse=True,
        bootable=False,
        active=True,
    )
    api.vms.get(VM0_NAME).disks.add(disk2_params)

    testlib.assert_true_within_short(
        lambda:
        api.vms.get(VM0_NAME).disks.get(DISK0_NAME).status.state == 'ok'
    )
    nt.assert_true(api.vms.get(VM0_NAME).disks.get(DISK0_NAME).active)


@testlib.with_ovirt_api
def hotunplug_disk(api):
    disk = api.vms.get(VM0_NAME).disks.get(DISK0_NAME)
    nt.assert_true(
        disk.deactivate()
    )

    testlib.assert_true_within_short(
        lambda:
        api.vms.get(VM0_NAME).disks.get(DISK0_NAME).active == False
    )


@testlib.with_ovirt_api
def suspend_resume_vm(api):
    nt.assert_true(api.vms.get(VM0_NAME).suspend())

    testlib.assert_true_within_long(
        lambda:
        api.vms.get(VM0_NAME).status.state == 'suspended'
    )

    nt.assert_true(api.vms.get(VM0_NAME).start())

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


_TEST_LIST = [
    add_vm_blank,
    add_vm_template,
    add_nic,
    add_disk,
    add_console,
    add_directlun,
    vm_run,
    suspend_resume_vm,
    template_export,
    hotplug_disk,
    disk_operations,
    hotplug_nic,
    hotunplug_disk,
    add_event,
    vdsm_recovery
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
