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
from ovirtsdk.xml import params
from ovirtlago import testlib
import nose.tools as nt

import ovirtsdk4.types as types

import test_utils
import time

MB = 2 ** 20
GB = 2 ** 30

TEST_CLUSTER = 'test-cluster'
TEST_DC = 'test-dc'
TEMPLATE_BLANK = 'Blank'

VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
VM_WITH_INTERFACE = 'vm-with-iface'

@testlib.with_ovirt_api
def add_vm_blank(api):
    vm_memory = 256 * MB
    vm_params = params.VM(
        memory=vm_memory,
        os=params.OperatingSystem(
            type_='other_linux',
            boot=[params.Boot(dev=types.BootDevice.HD),
                  params.Boot(dev=types.BootDevice.NETWORK)
                  ],
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
    vm_params.name = VM1_NAME
    api.vms.add(vm_params)
    testlib.assert_true_within_short(
        lambda: api.vms.get(VM1_NAME).status.state == 'down',
    )


@testlib.with_ovirt_prefix
def vm_run(prefix):
    engine = prefix.virt_env.engine_vm()
    api = engine.get_api()
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
                ),
            ),
        ),
    )
    api.vms.get(VM0_NAME).start(start_params)
    testlib.assert_true_within_long(
        lambda: api.vms.get(VM0_NAME).status.state == 'up',
    )


def _update_cluster_version(api, new_version):
    engine = api.system_service()
    clusters_service = engine.clusters_service()
    cluster = clusters_service.list(search=TEST_CLUSTER)[0]
    cluster_service = clusters_service.cluster_service(cluster.id)

    vms_service = engine.vms_service()

    old_version = types.Version(
        major=cluster.version.major,
        minor=cluster.version.minor
    )

    cluster_service.update(
        cluster=types.Cluster(
            version=new_version
        )
    )
    updating_version = clusters_service.list(search=TEST_CLUSTER)[0].version
    nt.assert_true(
        updating_version.major == new_version.major and
        updating_version.minor == new_version.minor
    )

    down_vm = vms_service.list(search=VM1_NAME)[0]
    nt.assert_true(down_vm.custom_compatibility_version is None)

    up_vm = vms_service.list(search=VM0_NAME)[0]
    nt.assert_true(
        up_vm.custom_compatibility_version.major == old_version.major and
        up_vm.custom_compatibility_version.minor == old_version.minor
    )
    nt.assert_true(up_vm.next_run_configuration_exists)

    events = engine.events_service()
    last_event = int(events.list(max=2)[0].id)

    vm_service = vms_service.vm_service(up_vm.id)
    vm_service.stop()
    testlib.assert_true_within_short(
        lambda:
        vms_service.list(search=VM0_NAME)[0].status == types.VmStatus.DOWN
    )
    events = engine.events_service()
    testlib.assert_true_within_long(
        lambda:
        (next(e for e in events.list(from_=last_event)
              if e.code == 253)).code == 253,
        allowed_exceptions=[StopIteration]
    )
    vm_service.start()
    testlib.assert_true_within_short(
        lambda:
        vms_service.list(search=VM0_NAME)[0].status == types.VmStatus.UP
    )

    up_vm = vms_service.list(search=VM0_NAME)[0]
    nt.assert_false(up_vm.next_run_configuration_exists)
    nt.assert_true(up_vm.custom_compatibility_version is None)


@testlib.with_ovirt_api4
def update_cluster_versions(api):
    versions = [(4, 3), (4, 4)]
    for major, minor in versions:
        _update_cluster_version(
            api=api,
            new_version=types.Version(
                major=major,
                minor=minor
            )
        )


@testlib.with_ovirt_prefix
def clean_hosts_yum_cache(prefix):
    hosts = prefix.virt_env.host_vms()
    for host in hosts:
        host.ssh(
            [
                'yum',
                'clean',
                'all',
            ]
        )


@testlib.with_ovirt_api4
def run_vm_with_interface(api):
    engine = api.system_service()
    vms = engine.vms_service()

    _wait_datacenter_up(api)

    vm = vms.list(search=VM_WITH_INTERFACE)[0]
    vm_service = vms.vm_service(vm.id)

    vm_service.start()
    _wait_vm_status(vm_service, types.VmStatus.UP)

    vm_service.stop()
    _wait_vm_status(vm_service, types.VmStatus.DOWN)


def _wait_vm_status(vm, status):
    testlib.assert_true_within_short(
        lambda:
        vm.get().status == status
    )


@testlib.with_ovirt_api4
def upgrade_hosts(api):
    engine = api.system_service()
    hosts = engine.hosts_service()

    host_list = hosts.list()

    for host in host_list:
        host_service = hosts.host_service(host.id)

        with test_utils.TestEvent(engine, [884, 885]):
            # HOST_AVAILABLE_UPDATES_STARTED(884)
            # HOST_AVAILABLE_UPDATES_FINISHED(885)
            host_service.upgrade_check()

        with test_utils.TestEvent(engine, [840, 15]):
            # HOST_UPGRADE_STARTED(840)
            # VDS_MAINTENANCE(15)
            host_service.upgrade(reboot=True)

    for host in host_list:
        host_service = hosts.host_service(host.id)
        _wait_host_status(host_service, types.HostStatus.UP)

    _wait_datacenter_up(api)


def _wait_host_status(host, status):
    testlib.assert_true_within_long(
        lambda: host.get().status == status
    )


def _wait_datacenter_up(api):
    engine = api.system_service()
    dcs = engine.data_centers_service()

    test_dc = dcs.data_center_service(dcs.list(search=TEST_DC)[0].id)
    testlib.assert_true_within_long(
        lambda: test_dc.get().status == types.DataCenterStatus.UP
    )


_TEST_LIST = [
    run_vm_with_interface,
    clean_hosts_yum_cache,
    upgrade_hosts,
    add_vm_blank,
    vm_run,
    update_cluster_versions
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
