#
# Copyright 2018 Red Hat, Inc.
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
import pytest

from lib import netlib
from lib import virtlib

import fixtures.virt


MAC_ADDR_1 = '00:1a:4a:16:01:50'
MAC_ADDR_2 = '00:1a:4a:16:01:51'
NIC_NAME = 'nic123'

VM0 = 'vm0'
VM1 = 'vm1'


def test_move_stateless_vm_mac_to_new_vm_fails(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):

    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name=VM0,
                    cluster=default_cluster.name,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME,
                    stateless=True)

        _create_vnic(vm_0, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        with vm_0.wait_for_up_status():
            vm_0.run()

        _replace_vnic_mac_addr(vm_0, MAC_ADDR_2)

        vm_1.create(vm_name=VM1,
                    cluster=default_cluster.name,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME,
                    stateless=True)

        with pytest.raises(netlib.MacAddrInUseError):
            _create_vnic(vm_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)


def test_move_mac_to_new_vm(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):

    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name=VM0,
                    cluster=default_cluster.name,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME,
                    stateless=False)

        _create_vnic(vm_0, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        with vm_0.wait_for_up_status():
            vm_0.run()

        _replace_vnic_mac_addr(vm_0, MAC_ADDR_2)

        vm_1.create(vm_name=VM1,
                    cluster=default_cluster.name,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME,
                    stateless=True)

        _create_vnic(vm_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        vnic_1 = vm_1.get_vnic(NIC_NAME)
        assert vnic_1.mac_address == MAC_ADDR_1


def _replace_vnic_mac_addr(vm, addr):
    vnic = vm.get_vnic(NIC_NAME)
    vnic.hotunplug()
    vnic.set_mac_addr(addr)
    vnic.hotplug()


def _create_vnic(vm, ovirtmgmt_vnic_profile, mac_addr):
    vnic = netlib.Vnic(vm)
    vnic.create(name=NIC_NAME,
                vnic_profile=ovirtmgmt_vnic_profile,
                mac_addr=mac_addr)
    with vm.wait_for_down_status():
        pass
