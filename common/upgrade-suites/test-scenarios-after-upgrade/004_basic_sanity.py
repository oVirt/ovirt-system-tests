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

MB = 2 ** 20
GB = 2 ** 30

TEST_CLUSTER = 'test-cluster'
TEMPLATE_BLANK = 'Blank'

VM0_NAME = 'vm0'
VM1_NAME = 'vm1'


@testlib.with_ovirt_api4
def add_vm_blank(api):

    # Get the vms service
    vms_service=api.system_service().vms_service()

    #Create VM from blank template
    vm_memory=256*MB
    vm=types.Vm(
        name=VM0_NAME,
        memory=vm_memory,
        type=types.VmType.SERVER,
        os=types.OperatingSystem(
            type='other_linux',
            boot=types.Boot(
                devices=[types.BootDevice.HD, types.BootDevice.NETWORK]
            ),
        ),
        high_availability=types.HighAvailability(
            enabled=False
        ),
        cluster=types.Cluster(
            name=TEST_CLUSTER
        ),
        template=types.Template(
            name=TEMPLATE_BLANK
        ),
        display=types.Display(
            smartcard_enabled=True,
            keyboard_layout='en-us',
            file_transfer_enabled=True,
            copy_paste_enabled=True
        ),
        memory_policy=types.MemoryPolicy(
            guaranteed=vm_memory//2
        )
    )

    #Add this VM
    vm=vms_service.add(vm)

    #Check that VM was added
    vm_service=vms_service.vm_service(vm.id)
    testlib.assert_true_within_short(
        lambda: vm_service.get().status == types.VmStatus.DOWN
    )

    #Add another VM
    vm.id=None
    vm.name=VM1_NAME
    vm.initialization=None
    vm=vms_service.add(vm)

    #Check that the second VM was added
    vm_service=vms_service.vm_service(vm.id)
    testlib.assert_true_within_short(
        lambda: vm_service.get().status == types.VmStatus.DOWN
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
    versions = [(4, 1), (4, 2)]
    for major, minor in versions:
        _update_cluster_version(
            api=api,
            new_version=types.Version(
                major=major,
                minor=minor
            )
        )


_TEST_LIST = [
    add_vm_blank,
    vm_run,
    update_cluster_versions
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
