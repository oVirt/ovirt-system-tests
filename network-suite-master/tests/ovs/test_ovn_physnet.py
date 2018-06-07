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
from lib import virtlib
from testlib.ping import ssh_ping


VNIC0_NAME = 'vnic0'
VM0_NAME = 'vm0'
OVN_PHYSNET_NAME = 'ovn_ovirtmgmt'


@pytest.fixture(scope='module')
def ovn_physnet(default_data_center, ovirtmgmt_network, ovs_cluster,
                default_ovn_provider, default_ovn_provider_client):
    """
    To remove an external logical network, the network has to be removed
    directly on its provider by OpenStack Networking API.
    The entity representing the external network inside oVirt engine
    has to be removed explicitly here, because auto_sync is disabled for the
    provider.
    """
    network = netlib.Network(default_data_center)
    network.create(OVN_PHYSNET_NAME,
                   external_provider=default_ovn_provider,
                   external_provider_physical_network=ovirtmgmt_network)
    try:
        cluster_network = clusterlib.ClusterNetwork(ovs_cluster)
        cluster_network.assign(network)
        yield network
    finally:
        network.remove()
        default_ovn_provider_client.delete_network(OVN_PHYSNET_NAME)


def test_connect_vm_to_external_physnet(system, ovs_cluster,
                                        cirros_template, ovn_physnet,
                                        host_in_ovs_cluster, host_0, host_1):
    with virtlib.vm_pool(system, size=1) as (vm_0,):
        vm_0.create(
            vm_name=VM0_NAME,
            cluster=ovs_cluster,
            template=cirros_template
        )

        vnic_profile_0 = netlib.VnicProfile(system)
        vnic_profile_0.import_by_name(ovn_physnet.name)

        vm_0_vnic_0 = netlib.Vnic(vm_0)
        vm_0_vnic_0.create(
            name=VNIC0_NAME,
            vnic_profile=vnic_profile_0
        )

        vm_0.wait_for_down_status()
        vm_0.run_once(cloud_init_hostname=VM0_NAME)
        vm_0.wait_for_up_status()

        other_host = _other_host(host_in_ovs_cluster, [host_0, host_1])
        ssh_ping(other_host.address, other_host.root_password, VM0_NAME)


def _other_host(host, candidates):
    return next(
        candidate for candidate in candidates if candidate.id != host.id
    )
