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

from lib import clusterlib
from lib import netlib
from lib import templatelib
from lib import virtlib

import fixtures.virt


MAC_ADDR_1 = '00:1a:4a:16:01:50'
MAC_ADDR_2 = '00:1a:4a:16:01:51'
NIC_NAME_1 = 'nic001'
NIC_NAME_2 = 'nic002'

VM0 = 'vm0'
VM1 = 'vm1'


@pytest.fixture(scope='module')
def host_1_in_cluster_0(default_data_center, host_1_up, cluster_0):
    current_cluster = host_1_up.get_cluster()

    host_1_up.change_cluster(cluster_0)
    default_data_center.wait_for_up_status()
    yield
    host_1_up.change_cluster(current_cluster)
    default_data_center.wait_for_up_status()


@pytest.fixture(scope='module')
def cluster_0(system, default_data_center):
    CLUSTER_0 = 'Cluster0'
    cluster = clusterlib.Cluster(system)
    cluster.create(default_data_center, CLUSTER_0)
    yield cluster
    cluster.remove()


def test_undo_preview_snapshot_when_mac_used_reassigns_a_new_mac(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):
    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name=VM0,
                    cluster=default_cluster,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME)
        with vm_0.wait_for_down_status():
            pass

        vm_0.run()
        vm_0.wait_for_up_status()

        nicless_snapshot = _create_snapshot(vm_0)

        vm_0_vnic_0 = netlib.Vnic(vm_0)
        vm_0_vnic_0.create(name=NIC_NAME_1,
                           vnic_profile=ovirtmgmt_vnic_profile,
                           mac_addr=MAC_ADDR_1)

        vm_0.stop()
        vm_0.wait_for_down_status()

        nicless_snapshot.preview()
        nicless_snapshot.wait_for_preview_status()

        vm_1.create(vm_name=VM1,
                    cluster=default_cluster,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME)
        vm_1_vnic_0 = netlib.Vnic(vm_1)
        vm_1_vnic_0.create(name=NIC_NAME_1,
                           vnic_profile=ovirtmgmt_vnic_profile,
                           mac_addr=MAC_ADDR_1)

        nicless_snapshot.undo_preview()

        assert vm_0.get_vnic(NIC_NAME_1).mac_address != MAC_ADDR_1


@pytest.mark.usefixtures('default_storage_domain', 'host_1_in_cluster_0')
def test_mac_pools_in_different_clusters_dont_overlap(
        system, cluster_0, default_cluster, ovirtmgmt_vnic_profile):
    MAC_POOL_0 = 'mac_pool_0'
    MAC_POOL_1 = 'mac_pool_1'
    MAC_POOL_START = '00:00:00:00:00:02'
    MAC_POOL_END = '00:00:00:00:00:15'

    # NOTE: Static MAC address assignments are independent from the MAC pool
    # range, i.e. it is possible to assign addresses outside the range to
    # vNics (this causes the static address to be added to the pool if it is
    # not already present). However, specifying ranges is required for MAC pool
    # initialization, and as such, arbitrary ranges are used.

    MAC_POOL_RANGES = (clusterlib.MacPoolRange(
        start=MAC_POOL_START, end=MAC_POOL_END),
    )

    default_cluster_mac_pool = clusterlib.mac_pool(
        system, default_cluster, MAC_POOL_0, MAC_POOL_RANGES
    )
    cluster_0_mac_pool = clusterlib.mac_pool(
        system, cluster_0, MAC_POOL_1, MAC_POOL_RANGES
    )
    with default_cluster_mac_pool, cluster_0_mac_pool:
        with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
            vm_0.create(vm_name=VM0,
                        cluster=default_cluster,
                        template=templatelib.TEMPLATE_BLANK)
            _create_vnic(
                vm_0, NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_POOL_START
            )

            vm_1.create(vm_name=VM1,
                        cluster=cluster_0,
                        template=templatelib.TEMPLATE_BLANK)
            with pytest.raises(netlib.MacAddrInUseError):
                _create_vnic(
                    vm_1, NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_POOL_START
                )


def test_restore_snapshot_with_an_used_mac_implicitly_assigns_new_mac(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):

    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name=VM0,
                    cluster=default_cluster,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME)
        _create_vnic(vm_0, NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        vm_0.run()
        vm_0.wait_for_up_status()

        snapshot = _create_snapshot(vm_0)

        _replace_vnic_mac_addr(vm_0, MAC_ADDR_2)

        vm_1.create(vm_name=VM1,
                    cluster=default_cluster,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME)
        _create_vnic(vm_1, NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        with vm_0.wait_for_down_status():
            vm_0.stop()

        snapshot.restore()

        vnic_0 = vm_0.get_vnic(NIC_NAME_1)
        assert vnic_0.mac_address != MAC_ADDR_1


def test_move_stateless_vm_mac_to_new_vm_fails(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):

    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name=VM0,
                    cluster=default_cluster,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME,
                    stateless=True)

        _create_vnic(vm_0, NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        vm_0.run()
        vm_0.wait_for_up_status()

        _replace_vnic_mac_addr(vm_0, MAC_ADDR_2)

        vm_1.create(vm_name=VM1,
                    cluster=default_cluster,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME)

        with pytest.raises(netlib.MacAddrInUseError):
            _create_vnic(vm_1, NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)


def test_move_mac_to_new_vm(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):

    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name=VM0,
                    cluster=default_cluster,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME)

        _create_vnic(vm_0, NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        vm_0.run()
        vm_0.wait_for_up_status()

        _replace_vnic_mac_addr(vm_0, MAC_ADDR_2)

        vm_1.create(vm_name=VM1,
                    cluster=default_cluster,
                    template=fixtures.virt.CIRROS_TEMPLATE_NAME)

        _create_vnic(vm_1, NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        vnic_1 = vm_1.get_vnic(NIC_NAME_1)
        assert vnic_1.mac_address == MAC_ADDR_1


def _replace_vnic_mac_addr(vm, addr):
    vnic = vm.get_vnic(NIC_NAME_1)
    vnic.hotunplug()
    vnic.set_mac_addr(addr)
    vnic.hotplug()


def _create_vnic(vm, vnic_name, ovirtmgmt_vnic_profile, mac_addr=None):
    vnic = netlib.Vnic(vm)
    vnic.create(name=vnic_name,
                vnic_profile=ovirtmgmt_vnic_profile,
                mac_addr=mac_addr)
    with vm.wait_for_down_status():
        pass


def _create_snapshot(vm):
    SNAPSHOT_DESC = 'snapshot0'

    snapshot = virtlib.VmSnapshot(vm)
    snapshot.create(SNAPSHOT_DESC)
    snapshot.wait_for_ready_status()
    return snapshot
