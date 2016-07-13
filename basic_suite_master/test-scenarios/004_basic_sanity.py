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
import os
import nose.tools as nt
from nose import SkipTest

from ovirtsdk.xml import params

from ovirtlago import testlib

# TODO: remove once lago can gracefully handle on-demand prefixes
def _get_prefixed_name(entity_name):
    suite = os.environ.get('SUITE')
    return (
        'lago_'
        + os.path.basename(suite).replace('.', '_')
        + '_' + entity_name
    )


MB = 2 ** 20
GB = 2 ** 30

TEST_DC = 'test-dc'
TEST_CLUSTER = 'test-cluster'
TEMPLATE_BLANK = 'Blank'
TEMPLATE_CENTOS7 = 'centos7_template'
TEMPLATE_CIRROS = 'CirrOS_0.3.4_for_x86_64_glance_template'

VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
DISK0_NAME = '%s_disk0' % VM0_NAME
DISK1_NAME = '%s_disk1' % VM0_NAME

SD_ISCSI_HOST_NAME = _get_prefixed_name('storage')
SD_ISCSI_TARGET = 'iqn.2014-07.org.ovirt:storage'
SD_ISCSI_PORT = 3260
SD_ISCSI_NR_LUNS = 2
DLUN_DISK_NAME = 'DirectLunDisk'
SD_TEMPLATES_NAME = 'templates'

@testlib.with_ovirt_api
def add_vm_blank(api):
    vm_memory = 512 * MB
    vm_params = params.VM(
        name=VM0_NAME,
        memory=vm_memory,
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
    api.vms.add(vm_params)
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'down',
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


@testlib.with_ovirt_api
def add_disk(api):
    disk_params = params.Disk(
        name=DISK0_NAME,
        size=10 * GB,
        provisioned_size=1,
        interface='virtio',
        format='cow',
        storage_domains=params.StorageDomains(
            storage_domain=[
                params.StorageDomain(
                    name='nfs',
                ),
            ],
        ),
        status=None,
        sparse=True,
        bootable=True,
    )
    api.vms.get(VM0_NAME).disks.add(disk_params)
    testlib.assert_true_within_short(
        lambda:
        api.vms.get(VM0_NAME).disks.get(DISK0_NAME).status.state == 'ok'
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
    ret = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ssh(['multipath', '-ll', '-v1', '|sort'])
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
                )
            ]
        ),
    )

    api = prefix.virt_env.engine_vm().get_api()
    api.vms.get(VM0_NAME).disks.add(dlun_params)
    nt.assert_not_equal(
        api.vms.get(VM0_NAME).disks.get(DLUN_DISK_NAME),
        None,
        'Direct LUN disk not attached'
    )


@testlib.with_ovirt_api
def snapshot_merge(api):
    dead_snap1_params = params.Snapshot(
        description='dead_snap1',
        persist_memorystate=False,
        disks=params.Disks(
            disk=[
                params.Disk(
                    id=api.vms.get(VM0_NAME).disks.get(DISK0_NAME).id,
                ),
            ],
        ),
    )
    api.vms.get(VM0_NAME).snapshots.add(dead_snap1_params)
    testlib.assert_true_within_short(
        lambda:
        api.vms.get(VM0_NAME).snapshots.list()[-1].snapshot_status == 'ok'
    )

    dead_snap2_params = params.Snapshot(
        description='dead_snap2',
        persist_memorystate=False,
        disks=params.Disks(
            disk=[
                params.Disk(
                    id=api.vms.get(VM0_NAME).disks.get(DISK0_NAME).id,
                ),
            ],
        ),
    )
    api.vms.get(VM0_NAME).snapshots.add(dead_snap2_params)
    testlib.assert_true_within_short(
        lambda:
        api.vms.get(VM0_NAME).snapshots.list()[-1].snapshot_status == 'ok'
    )

    api.vms.get(VM0_NAME).snapshots.list()[-2].delete()
    testlib.assert_true_within_short(
        lambda:
        (len(api.vms.get(VM0_NAME).snapshots.list()) == 2) and
        (api.vms.get(VM0_NAME).snapshots.list()[-1].snapshot_status
         == 'ok'),
    )


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
        vm=params.VM(
            placement_policy=params.VmPlacementPolicy(
                host=params.Host(
                    name=sorted(host_names)[0]
                ),
            ),
        ),
    )
    api.vms.get(VM0_NAME).start(start_params)
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'up',
    )


@testlib.with_ovirt_prefix
def vm_migrate(prefix):
    api = prefix.virt_env.engine_vm().get_api()
    host_names = [h.name() for h in prefix.virt_env.host_vms()]

    migrate_params = params.Action(
        host=params.Host(
            name=sorted(host_names)[1]
        ),
    )
    api.vms.get(VM0_NAME).migrate(migrate_params)
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'up',
    )


@testlib.with_ovirt_api
def template_export(api):
    api.templates.get(TEMPLATE_CIRROS).export(
        params.Action(
           storage_domain=api.storagedomains.get(SD_TEMPLATES_NAME)
        ),
    )

    testlib.assert_true_within_long(
        lambda: api.templates.get(TEMPLATE_CIRROS).status.state == 'ok',
    )


@testlib.host_capability(['snapshot-live-merge'])
@testlib.with_ovirt_api
def snapshot_live_merge(api):
    disk = api.vms.get(VM0_NAME).disks.list()[0]
    disk_id = disk.id
    disk_name = disk.name

    live_snap1_params = params.Snapshot(
        description='live_snap1',
        persist_memorystate=True,
        disks=params.Disks(
            disk=[
                params.Disk(
                    id=disk_id,
                ),
            ],
        ),
    )
    api.vms.get(VM0_NAME).snapshots.add(live_snap1_params)
    testlib.assert_true_within_short(
        lambda:
        api.vms.get(VM0_NAME).snapshots.list()[-1].snapshot_status == 'ok'
    )

    live_snap2_params = params.Snapshot(
        description='live_snap2',
        persist_memorystate=True,
        disks=params.Disks(
            disk=[
                params.Disk(
                    id=disk_id,
                ),
            ],
        ),
    )
    api.vms.get(VM0_NAME).snapshots.add(live_snap2_params)
    for i, _ in enumerate(api.vms.get(VM0_NAME).snapshots.list()):
        testlib.assert_true_within_short(
            lambda:
            (api.vms.get(VM0_NAME).snapshots.list()[i].snapshot_status
             == 'ok')
        )

    api.vms.get(VM0_NAME).snapshots.list()[-2].delete()

    testlib.assert_true_within_long(
        lambda: len(api.vms.get(VM0_NAME).snapshots.list()) == 2,
    )

    for i, _ in enumerate(api.vms.get(VM0_NAME).snapshots.list()):
        testlib.assert_true_within_long(
            lambda:
            (api.vms.get(VM0_NAME).snapshots.list()[i].snapshot_status
             == 'ok'),
        )
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'up'
    )

    testlib.assert_true_within_long(
        lambda:
        api.vms.get(VM0_NAME).disks.get(disk_name).status.state == 'ok'
    )


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
        name=DISK1_NAME,
        size=9 * GB,
        provisioned_size=2,
        interface='virtio',
        format='cow',
        storage_domains=params.StorageDomains(
            storage_domain=[
                params.StorageDomain(
                    name='iscsi',
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
        api.vms.get(VM0_NAME).disks.get(DISK1_NAME).status.state == 'ok'
    )
    nt.assert_true(api.vms.get(VM0_NAME).disks.get(DISK1_NAME).active)


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
    add_event,
    add_vm_blank,
    add_nic,
    add_disk,
    add_console,
    snapshot_merge,
    add_vm_template,
    add_directlun,
    vm_run,
    template_export,
    vm_migrate,
    snapshot_live_merge,
    hotplug_nic,
    hotplug_disk,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
