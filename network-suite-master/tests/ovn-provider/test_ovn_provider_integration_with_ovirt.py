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

from ovirtlib import clusterlib
from ovirtlib import netlib
from ovirtlib import templatelib
from ovirtlib import virtlib


VNIC0_NAME = 'nic001'
VM0_NAME = 'vm0'
VNIC0_MAC = '00:1a:4a:17:15:50'


@pytest.fixture(scope='module')
def running_vm_0(ovirt_external_network, system, default_cluster,
                 default_storage_domain):
    cluster_network = clusterlib.ClusterNetwork(default_cluster)
    cluster_network.assign(ovirt_external_network)
    with virtlib.vm_pool(system, size=1) as (vm_0,):
        vm_0.create(
            vm_name=VM0_NAME,
            cluster=default_cluster,
            template=templatelib.TEMPLATE_BLANK
        )
        disk = default_storage_domain.create_disk('disk1')
        vm_0.attach_disk(disk=disk)

        vnic_profile0 = netlib.VnicProfile(system)
        vnic_profile0.import_by_name(ovirt_external_network.name)

        vm0_vnic_0 = netlib.Vnic(vm_0)
        vm0_vnic_0.create(
            name=VNIC0_NAME,
            vnic_profile=vnic_profile0,
            mac_addr=VNIC0_MAC
        )

        vm_0.wait_for_down_status()
        vm_0.run()
        vm_0.wait_for_up_status()
        yield vm_0


def test_connect_vm_to_external_network(running_vm_0,
                                        default_ovn_provider_client):
    vm0_vnic_0 = running_vm_0.get_vnic(VNIC0_NAME)

    assert not vm0_vnic_0.vnic_profile.filter

    ovn_port = _lookup_port_by_device_id(
        vm0_vnic_0.id, default_ovn_provider_client)
    assert ovn_port
    assert vm0_vnic_0.mac_address == ovn_port.mac_address


def _lookup_port_by_device_id(vnic_id, default_ovn_provider_cloud):
    for port in default_ovn_provider_cloud.list_ports():
        device_id = port.get('device_id')
        if device_id and device_id == vnic_id:
            return port
    return None
