#
# Copyright 2018-2020 Red Hat, Inc.
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

from ovirtlib import clusterlib
from ovirtlib import netlib
from ovirtlib import templatelib
from ovirtlib import virtlib
from ovirtlib.sdkentity import EntityCreationError
from ovirtlib.templatelib import TEMPLATE_BLANK as BLANK
from testlib import suite

MAC_POOL = 'mac_pool'
MAC_ADDR_1 = '00:1a:4a:16:01:50'
MAC_ADDR_2 = '00:1a:4a:16:01:51'
MAC_ADDR_3 = '00:1a:4a:16:01:60'
MAC_ADDR_4 = '00:1a:4a:16:01:61'
MAC_ADDR_5 = '00:1a:4a:16:01:70'
MAC_ADDR_6 = '00:1a:4a:16:01:72'
MAC_POOL_RANGE = clusterlib.MacPoolRange(
    start=MAC_ADDR_1, end=MAC_ADDR_2
)
MAC_POOL_RANGE_1 = clusterlib.MacPoolRange(
    start=MAC_ADDR_3, end=MAC_ADDR_4
)
MAC_POOL_RANGE_3 = clusterlib.MacPoolRange(
    start=MAC_ADDR_5, end=MAC_ADDR_6
)
OVERLAP_REGEX = r".*MAC pool cannot contain ranges which overlap.*"

NIC_NAME_1 = 'nic001'
NIC_NAME_2 = 'nic002'


SNAPSHOT_DESC = 'snapshot0'


pytestmark = pytest.mark.usefixtures('default_storage_domain')


def test_set_mac_pool_duplicate_macs_from_true_to_false_while_dup_exists(
        system, default_cluster, ovirtmgmt_vnic_profile):
    with clusterlib.mac_pool(
        system, default_cluster, MAC_POOL, (MAC_POOL_RANGE,),
        allow_duplicates=True
    ) as mac_pool:
        with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
            vm_0.create(vm_name='test_set_mac_pool_duplicate_macs_vm_0',
                        cluster=default_cluster,
                        template=templatelib.TEMPLATE_BLANK)
            vm_1.create(vm_name='test_set_mac_pool_duplicate_macs_vm_1',
                        cluster=default_cluster,
                        template=templatelib.TEMPLATE_BLANK)

            vm_0.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)
            vm_0.wait_for_down_status()

            vm_1.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)
            vm_1.wait_for_down_status()

            with pytest.raises(clusterlib.MacPoolContainsDuplicatesError):
                mac_pool.set_allow_duplicates(False)


def test_assign_vnic_with_full_mac_pool_capacity_fails(
        system, default_cluster, ovirtmgmt_vnic_profile):
    NIC_NAME_3 = 'nic003'

    with clusterlib.mac_pool(
        system, default_cluster, MAC_POOL, (MAC_POOL_RANGE,)
    ):
        with virtlib.vm_pool(system, size=1) as (vm,):
            vm.create(vm_name='test_assign_vnic_with_full_mac_pool_vm_0',
                      cluster=default_cluster,
                      template=templatelib.TEMPLATE_BLANK)
            vm.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile)
            vm.create_vnic(NIC_NAME_2, ovirtmgmt_vnic_profile)

            with pytest.raises(netlib.MacPoolIsInFullCapacityError):
                vm.create_vnic(NIC_NAME_3, ovirtmgmt_vnic_profile)


def test_undo_preview_snapshot_when_mac_used_reassigns_a_new_mac(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):
    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name='test_undo_preview_snapshot_when_mac_used_vm_0',
                    cluster=default_cluster,
                    template=cirros_template)
        vm_0.wait_for_down_status()

        vm_0.run()
        vm_0.wait_for_up_status()

        nicless_snapshot = vm_0.create_snapshot(SNAPSHOT_DESC)

        vm_0.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)
        vm_0.stop()
        vm_0.wait_for_down_status()

        nicless_snapshot.preview()
        nicless_snapshot.wait_for_preview_status()

        vm_1.create(vm_name='test_undo_preview_snapshot_when_mac_used_vm_1',
                    cluster=default_cluster,
                    template=cirros_template)
        vm_1.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        nicless_snapshot.undo_preview()

        assert vm_0.get_vnic(NIC_NAME_1).mac_address != MAC_ADDR_1


@pytest.mark.usefixtures('host_0_in_cluster_0')
def test_mac_pools_in_different_clusters_dont_overlap(
        system, cluster_0, default_cluster, ovirtmgmt_vnic_profile):
    MAC_POOL_0 = 'mac_pool_0'
    MAC_POOL_1 = 'mac_pool_1'

    # NOTE: Static MAC address assignments are independent from the MAC pool
    # range, i.e. it is possible to assign addresses outside the range to
    # vNics (this causes the static address to be added to the pool if it is
    # not already present). However, specifying ranges is required for MAC pool
    # initialization, and as such, non-overlapping ranges are used.

    default_cluster_mac_pool = clusterlib.mac_pool(
        system, default_cluster, MAC_POOL_0, (MAC_POOL_RANGE,)
    )
    cluster_0_mac_pool = clusterlib.mac_pool(
        system, cluster_0, MAC_POOL_1, (MAC_POOL_RANGE_1,)
    )
    with default_cluster_mac_pool, cluster_0_mac_pool:
        with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
            vm_0.create(vm_name='test_mac_pools_in_different_clusters_vm_0',
                        cluster=default_cluster,
                        template=templatelib.TEMPLATE_BLANK)
            vm_0.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

            vm_1.create(vm_name='test_mac_pools_in_different_clusters_vm_1',
                        cluster=cluster_0,
                        template=templatelib.TEMPLATE_BLANK)
            with pytest.raises(netlib.MacAddrInUseError):
                vm_1.create_vnic(
                    NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1
                )


@suite.skip_suites_below('4.4')
def test_add_overlapping_mac_pool_same_cluster(system, cluster_0,
                                               default_cluster):
    POOL_0 = 'mac_pool_0'
    POOL_1 = 'mac_pool_1'
    default_cluster_mac_pool = clusterlib.mac_pool(
        system, default_cluster, POOL_0, (MAC_POOL_RANGE,)
    )
    default_cluster_mac_pool_1 = clusterlib.mac_pool(
        system, default_cluster, POOL_1, (MAC_POOL_RANGE,)
    )
    with pytest.raises(EntityCreationError, match=OVERLAP_REGEX):
        with default_cluster_mac_pool, default_cluster_mac_pool_1:
            pass


@suite.skip_suites_below('4.4')
def test_add_overlapping_mac_pool_other_cluster(system, cluster_0,
                                                default_cluster):
    POOL_0 = 'mac_pool_0'
    POOL_1 = 'mac_pool_1'
    default_cluster_mac_pool = clusterlib.mac_pool(
        system, default_cluster, POOL_0, (MAC_POOL_RANGE,)
    )
    cluster_0_mac_pool = clusterlib.mac_pool(
        system, cluster_0, POOL_1, (MAC_POOL_RANGE,)
    )
    with pytest.raises(EntityCreationError, match=OVERLAP_REGEX):
        with default_cluster_mac_pool, cluster_0_mac_pool:
            pass


def test_restore_snapshot_with_an_used_mac_implicitly_assigns_new_mac(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):

    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name='test_restore_snapshot_with_an_used_mac_vm_0',
                    cluster=default_cluster,
                    template=cirros_template)
        vnic_0 = vm_0.create_vnic(NIC_NAME_1,
                                  ovirtmgmt_vnic_profile, MAC_ADDR_1)
        vm_0.wait_for_down_status()

        vm_0.run()
        vm_0.wait_for_up_status()

        snapshot = vm_0.create_snapshot(SNAPSHOT_DESC)

        vnic_0.hot_replace_mac_addr(MAC_ADDR_2)

        vm_1.create(vm_name='test_restore_snapshot_with_an_used_mac_vm_1',
                    cluster=default_cluster,
                    template=cirros_template)
        vm_1.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)

        vm_0.stop()
        vm_0.wait_for_down_status()

        snapshot.restore()

        vnic_0 = vm_0.get_vnic(NIC_NAME_1)
        assert vnic_0.mac_address != MAC_ADDR_1


def test_move_stateless_vm_mac_to_new_vm_fails(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):

    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name='test_move_stateless_vm_mac_to_new_vm_fails_vm_0',
                    cluster=default_cluster,
                    template=cirros_template,
                    stateless=True)

        vnic_0 = vm_0.create_vnic(NIC_NAME_1,
                                  ovirtmgmt_vnic_profile, MAC_ADDR_1)
        vm_0.wait_for_down_status()

        vm_0.run()
        vm_0.wait_for_up_status()

        vnic_0.hot_replace_mac_addr(MAC_ADDR_2)

        vm_1.create(vm_name='test_move_stateless_vm_mac_to_new_vm_fails_vm_1',
                    cluster=default_cluster,
                    template=cirros_template)

        with pytest.raises(netlib.MacAddrInUseError):
            vm_1.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile, MAC_ADDR_1)


def test_move_mac_to_new_vm(
        system, default_cluster, ovirtmgmt_vnic_profile, cirros_template):
    mac_addr_1 = '00:1a:4a:16:01:81'
    mac_addr_2 = '00:1a:4a:16:01:82'
    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vm_0.create(vm_name='test_move_mac_to_new_vm_0',
                    cluster=default_cluster,
                    template=cirros_template)

        vnic_0 = vm_0.create_vnic(NIC_NAME_1,
                                  ovirtmgmt_vnic_profile, mac_addr_1)
        vm_0.wait_for_down_status()

        vm_0.run()
        vm_0.wait_for_up_status()

        vnic_0.hot_replace_mac_addr(mac_addr_2)

        vm_1.create(vm_name='test_move_mac_to_new_vm_1',
                    cluster=default_cluster,
                    template=cirros_template)

        vm_1.create_vnic(NIC_NAME_1, ovirtmgmt_vnic_profile, mac_addr_1)

        vnic_1 = vm_1.get_vnic(NIC_NAME_1)
        assert vnic_1.mac_address == mac_addr_1


@suite.skip_suites_below('4.4')
@pytest.mark.usefixtures('pool_0_cluster_0', 'pool_1_cluster_1')
@pytest.mark.usefixtures('host_0_in_cluster_0', 'host_1_in_cluster_1')
def test_allocate_mac_in_use_in_other_cluster_small_mac_pool(
        system, default_data_center, cluster_0, cluster_1):
    """
    A 2-address pool is exhausted by the flow and the pool is tested for being
    able to find another free and unused address.
    """
    _run_scenario_of_bz_1760170(
        system, default_data_center, cluster_0, cluster_1)


@suite.skip_suites_below('4.4')
@pytest.mark.usefixtures('pool_3_cluster_0', 'pool_1_cluster_1')
@pytest.mark.usefixtures('host_0_in_cluster_0', 'host_1_in_cluster_1')
def test_allocate_mac_in_use_in_other_cluster_large_mac_pool(
        system, default_data_center, cluster_0, cluster_1):
    """
    A 3-address pool has the pointer pointing to a free and unused address
    after vm_1 is created so the pool is tested for allocating this address.
    """
    _run_scenario_of_bz_1760170(
        system, default_data_center, cluster_0, cluster_1)


def _run_scenario_of_bz_1760170(system, default_dc, cluster_0, cluster_1):
    """
    The BZ shows that the pool allocates an address which is used in another
    pool, although there is another unused address in the pool.
    Tricking the allocation pointer to point to a used address is achieved by
    exhausting the free addresses in the pool and then removing a vnic so that
    there is a free and unused address to allocate, but the pointer points to a
    used address and therefore it is wrongly allocated because usability is not
    checked.
    Flow:
    - on cluster_0 (pool_0) create vm_0 with 2 vnics
    - remove the second vnic
    - move vm_0 to cluster_1 (pool_1)
    - create vm_1 on cluster_0
    - create a vnic on vm_1: this fails because the allocated address is in use
      on vm_0, but it should not fail because there is another free address on
      pool_0
    """
    NET_NAME = 'net_bz_1760170'
    with clusterlib.new_assigned_network(
            NET_NAME, default_dc, cluster_0) as net:
        with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
            vm_0.create(vm_name='_run_scenario_of_bz_1760170_vm_0',
                        cluster=cluster_0, template=BLANK)
            vm_0.wait_for_down_status()
            vm_0.create_vnic(
                netlib.OVIRTMGMT,
                default_dc.get_mgmt_network().vnic_profile()
            )
            vnic = vm_0.create_vnic(NET_NAME, net.vnic_profile())
            vnic.remove()
            vm_0.move_to_cluster(cluster_1)

            vm_1.create(vm_name='_run_scenario_of_bz_1760170_vm_1',
                        cluster=cluster_0, template=BLANK)
            vm_1.wait_for_down_status()
            vm_1.create_vnic(NET_NAME, net.vnic_profile())


@pytest.fixture(scope='function')
def host_0_in_cluster_0(host_0_up, cluster_0):
    with host_0_up.toggle_cluster(cluster_0):
        yield


@pytest.fixture(scope='function')
def host_1_in_cluster_1(host_1_up, cluster_1):
    with host_1_up.toggle_cluster(cluster_1):
        yield


@pytest.fixture(scope='module')
def cluster_0(system, default_data_center):
    with clusterlib.cluster(system, default_data_center, 'c0') as c0:
        yield c0


@pytest.fixture(scope='module')
def cluster_1(system, default_data_center):
    with clusterlib.cluster(system, default_data_center, 'c1') as c1:
        yield c1


@pytest.fixture(scope='function')
def pool_0_cluster_0(system, cluster_0):
    with clusterlib.mac_pool(system, cluster_0, 'p0', (MAC_POOL_RANGE,)) as p0:
        yield p0


@pytest.fixture(scope='function')
def pool_1_cluster_1(system, cluster_1):
    with clusterlib.mac_pool(
            system, cluster_1, 'p1', (MAC_POOL_RANGE_1,)) as p1:
        yield p1


@pytest.fixture(scope='function')
def pool_3_cluster_0(system, cluster_0):
    with clusterlib.mac_pool(
            system, cluster_0, 'p3', (MAC_POOL_RANGE_3,)) as p3:
        yield p3
