#
# Copyright 2017-2018 Red Hat, Inc.
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

from lib import virtlib
from lib import netlib
from lib import hostlib
from lib import clusterlib
from lib import datacenterlib
from lib import templatelib

ETH1 = 'eth1'
VM0 = 'vm0'
MIG_NET = 'mig-net'
MIG_NET_IPv4_ADDR_1 = '192.0.3.1'
MIG_NET_IPv4_ADDR_2 = '192.0.3.2'
MIG_NET_IPv4_MASK = '255.255.255.0'
NIC_NAME = 'nic1'


def _attach_new_vnic(vm, vnic_profile):
    vnic = netlib.Vnic(vm)
    vnic.create(name=NIC_NAME, vnic_profile=vnic_profile)
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
        yield vm


@pytest.fixture
def host_0_with_mig_net(migration_network, host_0_up):
    ip_config = netlib.create_static_ip_config_assignment(
        addr=MIG_NET_IPv4_ADDR_1, mask=MIG_NET_IPv4_MASK)
    mig_att_data = hostlib.NetworkAttachmentData(
        migration_network, ETH1, [ip_config])
    host_0_up.setup_networks([mig_att_data])
    yield host_0_up
    host_0_up.remove_networks((migration_network,))


@pytest.fixture
def host_1_with_mig_net(migration_network, host_1_up):
    ip_config = netlib.create_static_ip_config_assignment(
        addr=MIG_NET_IPv4_ADDR_2, mask=MIG_NET_IPv4_MASK)
    mig_att_data = hostlib.NetworkAttachmentData(
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
    vnic = running_vm_0.get_vnic(NIC_NAME)
    assert vnic.linked is True

    vnic.set_linked(False)
    vnic = running_vm_0.get_vnic(NIC_NAME)
    assert not vnic.linked

    vnic.set_linked(True)
    vnic = running_vm_0.get_vnic(NIC_NAME)
    assert vnic.linked is True


def test_iterators(running_vm_0, system):
    vm_names = (vm.name for vm in virtlib.Vm.iterate(system))
    assert running_vm_0.name in vm_names

    cluster_names = (cluster.name for cluster
                     in clusterlib.Cluster.iterate(system))
    assert running_vm_0.cluster.name in cluster_names

    vnic_names = (vnic.name for vnic in running_vm_0.vnics())
    assert NIC_NAME in vnic_names

    vnic_profile_names = (profile.name for profile
                          in netlib.VnicProfile.iterate(system))
    assert next(running_vm_0.vnics()).vnic_profile.name in vnic_profile_names

    dc_names = (dc.name for dc in datacenterlib.DataCenter.iterate(system))
    assert running_vm_0.cluster.get_data_center().name in dc_names

    assert len(list(datacenterlib.DataCenter.iterate(
        system, search='name = missing'))) == 0
