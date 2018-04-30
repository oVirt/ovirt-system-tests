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
from lib import clusterlib
from lib import netlib
from lib import templatelib
from lib import virtlib


VNIC0_NAME = 'nic001'
VM0_NAME = 'vm0'
VNIC0_MAC = '00:1a:4a:17:15:50'


def test_connect_vm_to_external_network(ovirt_external_network, system,
                                        default_cluster,
                                        default_ovn_provider_client,
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

        assert any(vm0_vnic_0.mac_address == port.mac_address
                   for port in default_ovn_provider_client.list_ports())
