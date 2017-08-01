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
TEMPLATE_CIRROS = 'CirrOS_0.3.5_for_x86_64_glance_template'

SD_NFS_NAME = 'nfs'
SD_SECOND_NFS_NAME = 'second-nfs'
SD_ISCSI_NAME = 'iscsi'

VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
VM2_NAME = 'vm2'
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

NETWORK_FILTER_NAME = 'clean-traffic'
NETWORK_FILTER_PARAMETER0_NAME = 'CTRL_IP_LEARNING'
NETWORK_FILTER_PARAMETER0_VALUE = 'dhcp'
NETWORK_FILTER_PARAMETER1_NAME = 'DHCPSERVER'
NETWORK_FILTER_PARAMETER1_VALUE = '192.168.201.1'


def _get_network_fiter_parameters_service(engine):
    nics_service = _get_nics_service(engine)
    nic = nics_service.list()[0]
    return nics_service.nic_service(id=nic.id)\
        .network_filter_parameters_service()


def _get_nics_service(engine):
    vm_service = _get_vm_service(engine)
    nics_service = vm_service.nics_service()
    return nics_service


def _get_vm_service(engine):
    vms_service = engine.vms_service()
    vm = vms_service.list(search=VM0_NAME)[0]
    return vms_service.vm_service(vm.id)


@testlib.with_ovirt_api
def add_vm_blank(api):
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


@testlib.with_ovirt_api4
def add_disk(api):
    engine = api.system_service()
    vms_service = engine.vms_service()
    vm = vms_service.list(search=VM0_NAME)[0]
    vm_service = vms_service.vm_service(vm.id)

    disks_service = engine.disks_service()
    disk = disks_service.list(search=GLANCE_DISK_NAME)[0]
    glance_disk = disks_service.disk_service(disk.id)
    nt.assert_true(vm_service and glance_disk)

    vm_service.disk_attachments_service().add(
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

        vm_service = vms_service.vm_service(vms_service.list(search=vm_name)[0].id)
        nt.assert_true(
            vm_service.disk_attachments_service().add(types.DiskAttachment(
                disk=disk_params,
                interface=types.DiskInterface.VIRTIO))
        )

    for disk_name in (GLANCE_DISK_NAME, DISK1_NAME, DISK2_NAME):
        testlib.assert_true_within_short(
            lambda:
            disks_service.disk_service(disks_service.list(search=disk_name)[0].id).get().status == types.DiskStatus.OK
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
    lun_guid = all_guids[SD_ISCSI_NR_LUNS]  # Take the first unused LUN. 0-(SD_ISCSI_NR_LUNS) are used by iSCSI SD

    dlun_params = types.Disk(
        name=DLUN_DISK_NAME,
        format=types.DiskFormat.RAW,
        lun_storage=types.HostStorage(
            type=types.StorageType.ISCSI,
            logical_units=[
                types.LogicalUnit(
                    address=prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ip(),
                    port=SD_ISCSI_PORT,
                    target=SD_ISCSI_TARGET,
                    id=lun_guid,
                    username='username',
                    password='password',
                )
            ]
        ),
        sgio=types.ScsiGenericIO.UNFILTERED,
    )

    api = prefix.virt_env.engine_vm().get_api_v4()
    vms_service = api.system_service().vms_service()
    vm_service = vms_service.vm_service(vms_service.list(search=VM0_NAME)[0].id)
    vm_service.disk_attachments_service().add(types.DiskAttachment(
        disk=dlun_params,
        interface=types.DiskInterface.VIRTIO_SCSI))

    disks_service = api.system_service().disks_service()
    disk = disks_service.disk_service(disks_service.list(search=DLUN_DISK_NAME)[0].id)
    nt.assert_not_equal(
        vm_service.disk_attachments_service().attachment_service(disk.get().id).get(),
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
    time.sleep(3)


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


@testlib.with_ovirt_api4
def add_filter(ovirt_api4):
    engine = ovirt_api4.system_service()
    nics_service = _get_nics_service(engine)
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


@testlib.with_ovirt_api4
def add_filter_parameter(ovirt_api4):
    network_filter_parameters_service = _get_network_fiter_parameters_service(
        ovirt_api4.system_service())

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
                value=NETWORK_FILTER_PARAMETER1_VALUE
            )
        )
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


@testlib.with_ovirt_api4
def template_export(api):
    templates_service = api.system_service().templates_service()
    template_cirros = templates_service.template_service(templates_service.list(search=TEMPLATE_CIRROS)[0].id)

    if template_cirros is None:
        raise SkipTest('{0}: template {1} is missing'.format(
            template_export.__name__,
            TEMPLATE_CIRROS
            )
        )

    storage_domain = api.system_service().storage_domains_service().list(search=SD_TEMPLATES_NAME)[0]
    template_cirros.export(
        storage_domain=types.StorageDomain(
            id=storage_domain.id,
        ),
    )
    testlib.assert_true_within_long(
        lambda:
        templates_service.template_service(template_cirros.get().id).get().status == types.TemplateStatus.OK,
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
    testlib.assert_true_within_short(
        lambda:
        engine.vms_service().list(search=VMPOOL_NAME+'-1')[0].status == types.VmStatus.DOWN,
        allowed_exceptions=[IndexError]
    )


@testlib.with_ovirt_api4
def update_vm_pool(api):
    pools_service= api.system_service().vm_pools_service()
    pool_id = pools_service.list(search=VMPOOL_NAME)[0].id
    pool_service = pools_service.pool_service(id=pool_id)

    pool_service.update(
        pool=types.VmPool(
            max_user_vms=2
        )
    )
    nt.assert_true(
        api.system_service().vm_pools_service().list(search=VMPOOL_NAME)[0].max_user_vms == 2
    )


@testlib.with_ovirt_api4
def remove_vm_pool(api):
    pools_service = api.system_service().vm_pools_service()
    pool_id = pools_service.list(search=VMPOOL_NAME)[0].id
    pools_service.pool_service(id=pool_id).remove()
    nt.assert_true(
         len(api.system_service().vm_pools_service().list()) == 0
    )


@testlib.with_ovirt_api4
def template_update(api):
    templates_service = api.system_service().templates_service()
    template_cirros = templates_service.template_service(templates_service.list(search=TEMPLATE_CIRROS)[0].id)

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
        templates_service.template_service(template_cirros.get().id).get().status == types.TemplateStatus.OK
    )
    nt.assert_true(templates_service.list(search=TEMPLATE_CIRROS)[0].comment == new_comment)


@testlib.with_ovirt_api
def disk_operations(api):
    vt = utils.VectorThread(
        [
            functools.partial(live_storage_migration),
            functools.partial(snapshot_cold_merge, api),
        ],
    )
    vt.start_all()
    vt.join_all()


@testlib.with_ovirt_api4
def hotplug_memory(api):
    engine = api.system_service()
    vms_service = engine.vms_service()
    vm = vms_service.list(search=VM0_NAME)[0]
    vm_service = vms_service.vm_service(vm.id)
    new_memory = vm.memory * 2
    vm_service.update(
        vm=types.Vm(
            memory=new_memory
        )
    )
    nt.assert_true(
        vms_service.list(search=VM0_NAME)[0].memory == new_memory
    )


@testlib.with_ovirt_api4
def hotplug_cpu(api):
    engine = api.system_service()
    vms_service = engine.vms_service()
    vm = vms_service.list(search=VM0_NAME)[0]
    vm_service = vms_service.vm_service(vm.id)
    new_cpu = vm.cpu
    new_cpu.topology.sockets = 2
    vm_service.update(
        vm=types.Vm(
            cpu=new_cpu
        )
    )
    nt.assert_true(
        vms_service.list(search=VM0_NAME)[0].cpu.topology.sockets == 2
    )

@testlib.with_ovirt_api4
def next_run_unplug_cpu(api):
    engine = api.system_service()
    vms_service = engine.vms_service()
    vm = vms_service.list(search=VM0_NAME)[0]
    vm_service = vms_service.vm_service(vm.id)
    new_cpu = vm.cpu
    new_cpu.topology.sockets = 1
    vm_service.update(
        vm=types.Vm(
            cpu=new_cpu,
        ),
        next_run=True
    )
    nt.assert_true(
        vms_service.list(search=VM0_NAME)[0].cpu.topology.sockets == 2
    )
    nt.assert_true(
    	vms_service.vm_service(vm.id).get(next_run=True).cpu.topology.sockets == 1
    )
    vm_service.reboot()
    testlib.assert_true_within_long(
        lambda:
         vms_service.list(search=VM0_NAME)[0].status == types.VmStatus.UP
    )
    nt.assert_true(
        vms_service.list(search=VM0_NAME)[0].cpu.topology.sockets == 1
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


@testlib.with_ovirt_api4
def hotplug_disk(api):
    vms_service = api.system_service().vms_service()
    vm_service = vms_service.vm_service(vms_service.list(search=VM0_NAME)[0].id)
    disk_attachments_service = vm_service.disk_attachments_service()
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

    testlib.assert_true_within_short(
        lambda:
        disk_attachments_service.attachment_service(disk_attachment.id).get().active and
        disk_service.get().status == types.DiskStatus.OK
    )


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
    add_vm_pool,
    update_vm_pool,
    remove_vm_pool,
    add_nic,
    add_disk,
    add_console,
    add_directlun,
    add_filter,
    add_filter_parameter,
    vm_run,
    suspend_resume_vm,
    template_export,
    template_update,
    hotplug_memory,
    hotplug_cpu,
    next_run_unplug_cpu,
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
