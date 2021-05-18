#
# Copyright 2017-2020 Red Hat, Inc.
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

from ovirtlib import virtlib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import clusterlib
from ovirtlib import joblib
from ovirtlib import datacenterlib
from ovirtlib import templatelib
from testlib import suite

ETH1 = 'eth1'
VM0 = 'test_vm_operations_vm_0'
MIG_NET = 'mig-net'
MIG_NET_IPv4_ADDR_1 = '192.0.3.1'
MIG_NET_IPv4_ADDR_2 = '192.0.3.2'
MIG_NET_IPv4_MASK = '255.255.255.0'
NIC1_NAME = 'nic1'
NIC2_NAME = 'nic2'


def _attach_new_vnic(vm, vnic_profile):
    vnic = netlib.Vnic(vm)
    vnic.create(name=NIC1_NAME, vnic_profile=vnic_profile)
    vm.wait_for_down_status()


@pytest.fixture
def migration_network(host_0, host_1, default_data_center, default_cluster):
    network = netlib.Network(default_data_center)
    network.create(name=MIG_NET, usages=())
    cluster_network = clusterlib.ClusterNetwork(default_cluster)
    cluster_network.assign(network)
    cluster_network.set_usages([netlib.NetworkUsage.MIGRATION])
    yield network
    network.remove()


@pytest.fixture(scope='module')
def running_vm_0(system, default_cluster, default_storage_domain,
                 ovirtmgmt_vnic_profile):
    disk = default_storage_domain.create_disk('disk0')
    with virtlib.vm_pool(system, size=1) as (vm,):
        vm.create(vm_name=VM0,
                  cluster=default_cluster,
                  template=templatelib.TEMPLATE_BLANK)

        _attach_new_vnic(vm, ovirtmgmt_vnic_profile)

        disk_att_id = vm.attach_disk(disk=disk)
        vm.wait_for_disk_up_status(disk, disk_att_id)
        vm.run()
        vm.wait_for_up_status()
        joblib.LaunchVmJobs(system).wait_for_done()
        yield vm


@pytest.fixture
def host_0_with_mig_net(migration_network, host_0_up):
    ip_assign = netattachlib.StaticIpAssignment(
        addr=MIG_NET_IPv4_ADDR_1, mask=MIG_NET_IPv4_MASK)
    mig_att_data = netattachlib.NetworkAttachmentData(
        migration_network, ETH1, [ip_assign])
    host_0_up.setup_networks([mig_att_data])
    yield host_0_up
    host_0_up.remove_networks((migration_network,))


@pytest.fixture
def host_1_with_mig_net(migration_network, host_1_up):
    ip_config = netattachlib.StaticIpAssignment(
        addr=MIG_NET_IPv4_ADDR_2, mask=MIG_NET_IPv4_MASK)
    mig_att_data = netattachlib.NetworkAttachmentData(
        migration_network, ETH1, [ip_config])
    host_1_up.setup_networks([mig_att_data])
    yield host_1_up
    host_1_up.remove_networks((migration_network,))


def test_live_vm_migration_using_dedicated_network(running_vm_0,
                                                   host_0_with_mig_net,
                                                   host_1_with_mig_net):
    dst_host = (host_0_with_mig_net
                if running_vm_0.host.id == host_1_with_mig_net.id
                else host_1_with_mig_net)

    running_vm_0.migrate(dst_host.name)
    running_vm_0.wait_for_up_status()

    # TODO: verify migration was carried via the dedicated network
    assert running_vm_0.host.id == dst_host.id


def test_hot_linking_vnic(running_vm_0):
    vnic = running_vm_0.get_vnic(NIC1_NAME)
    assert vnic.linked is True

    vnic.linked = False
    vnic = running_vm_0.get_vnic(NIC1_NAME)
    assert not vnic.linked

    vnic.linked = True
    vnic = running_vm_0.get_vnic(NIC1_NAME)
    assert vnic.linked is True


def test_iterators(running_vm_0, system):
    vm_names = (vm.name for vm in virtlib.Vm.iterate(system))
    assert running_vm_0.name in vm_names

    cluster_names = (cluster.name for cluster
                     in clusterlib.Cluster.iterate(system))
    assert running_vm_0.cluster.name in cluster_names

    vnic_names = (vnic.name for vnic in running_vm_0.vnics())
    assert NIC1_NAME in vnic_names

    vnic_profile_names = (profile.name for profile
                          in netlib.VnicProfile.iterate(system))
    assert next(running_vm_0.vnics()).vnic_profile.name in vnic_profile_names

    dc_names = (dc.name for dc in datacenterlib.DataCenter.iterate(system))
    assert running_vm_0.cluster.get_data_center().name in dc_names

    assert len(list(datacenterlib.DataCenter.iterate(
        system, search='name = missing'))) == 0


def test_assign_network_filter(running_vm_0, system, ovirtmgmt_network):
    with netlib.create_vnic_profile(system, 'temporary',
                                    ovirtmgmt_network) as profile:
        network_filter = netlib.NetworkFilter(system)
        network_filter.import_by_name('allow-dhcp')
        profile.filter = network_filter

        vnic = next(running_vm_0.vnics())
        original_profile = vnic.vnic_profile

        try:
            vnic.vnic_profile = profile
            assert vnic.vnic_profile.name == 'temporary'
            assert vnic.vnic_profile.filter.name == 'allow-dhcp'
        finally:
            vnic.vnic_profile = original_profile


@suite.skip_suites_below('4.3')
def test_hot_update_vm_interface(running_vm_0, ovirtmgmt_vnic_profile):
    vnic = netlib.Vnic(running_vm_0)
    vnic.create(name=NIC2_NAME, vnic_profile=netlib.EmptyVnicProfile())
    assert not vnic.vnic_profile.id

    vnic.vnic_profile = ovirtmgmt_vnic_profile
    assert vnic.vnic_profile.name == ovirtmgmt_vnic_profile.name

    vnic.vnic_profile = netlib.EmptyVnicProfile()
    assert not vnic.vnic_profile.id
