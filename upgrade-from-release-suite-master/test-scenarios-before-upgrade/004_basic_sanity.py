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

import ovirtsdk4.types as types

TEST_CLUSTER = 'test-cluster'
TEMPLATE_BLANK = 'Blank'

VM_NAME = 'vm-with-iface'
TEMPLATE_NAME = 'vm-with-iface-template'
TEMPLATE_SUBVERSION_NAME = 'vm-with-iface-subtemplate'

MGMT_NETWORK = 'ovirtmgmt'


@testlib.with_ovirt_api4
def add_vm_blank(api):
    engine = api.system_service()
    vms = engine.vms_service()

    new_vm = types.Vm(
        os=types.OperatingSystem(
            type='other_linux',
            boot=types.Boot(devices=[types.BootDevice.NETWORK])
        ),
        type=types.VmType.SERVER,
        cluster=types.Cluster(name=TEST_CLUSTER),
        template=types.Template(name=TEMPLATE_BLANK),
        name=VM_NAME
    )
    new_vm = vms.add(new_vm)

    vm_service = vms.vm_service(new_vm.id)
    testlib.assert_true_within_short(
        lambda: vm_service.get().status == types.VmStatus.DOWN
    )


@testlib.with_ovirt_api4
def add_nic(api):
    engine = api.system_service()
    vms = engine.vms_service()
    vm = vms.list(search=VM_NAME)[0]

    new_nic = types.Nic(
        name='eth0',
        interface=types.NicInterface.VIRTIO,
        network=types.Network(name=MGMT_NETWORK)
    )
    vms.vm_service(vm.id).nics_service().add(new_nic)


@testlib.with_ovirt_api4
def create_template_and_subversion(api):
    engine = api.system_service()

    templates = engine.templates_service()

    template = types.Template(
        name=TEMPLATE_NAME,
        vm=types.Vm(name=VM_NAME)
    )

    created_template = templates.add(template=template)
    _wait_template_status_ok(templates, created_template.id)

    template.version = types.TemplateVersion(
        version_name=TEMPLATE_SUBVERSION_NAME,
        base_template=types.Template(
            id=created_template.id
        )
    )
    created_template = templates.add(template)
    _wait_template_status_ok(templates, created_template.id)


def _wait_template_status_ok(templates, template_id):
    template = templates.template_service(template_id)
    testlib.assert_true_within_long(
        lambda: template.get().status == types.TemplateStatus.OK
    )


_TEST_LIST = [
    add_vm_blank,
    add_nic,
    create_template_and_subversion
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
