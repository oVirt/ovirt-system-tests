# Copyright 2021 Red Hat, Inc.
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
import pytest

from fixtures.host import ETH1

from ovirtlib import clusterlib
from ovirtlib import hostlib
from ovirtlib import joblib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import sshlib
from ovirtlib import virtlib


VM0_NAME = 'test_port_isolation_vm_0'
VM1_NAME = 'test_port_isolation_vm_1'
VNIC0_NAME = 'eth0'
PORT_ISOLATED_VNIC = 'eth1'
PORT_ISOLATION_NET = 'test_port_isolation_net'
VM_USERNAME = 'cirros'
VM_PASSWORD = 'gocubsgo'
PING_FAILED = '100% packet loss'


def test_ping_to_external_port_succeeds(vm_nodes, isolated_vnics_up_with_ip):
    for vm_node in vm_nodes:
        vm_node.ping4('8.8.8.8', PORT_ISOLATED_VNIC)


def test_ping_to_isolated_port_fails(vm_nodes, isolated_vnics_up_with_ip):
    with pytest.raises(sshlib.SshException, match=PING_FAILED):
        vm_nodes[0].ping4(isolated_vnics_up_with_ip[1], PORT_ISOLATED_VNIC)
    with pytest.raises(sshlib.SshException, match=PING_FAILED):
        vm_nodes[1].ping4(isolated_vnics_up_with_ip[0], PORT_ISOLATED_VNIC)


@pytest.fixture(scope='module')
def vms_ovirtmgmt_ip(host_1_up, vms_up_on_same_host):
    vms_ovirtmgmt_ip = []
    host_node = sshlib.Node(host_1_up.address, host_1_up.root_password)
    for name in [VM0_NAME, VM1_NAME]:
        ovirtmgmt_ip = host_node.lookup_ip_address_with_dns_query(name)
        vms_ovirtmgmt_ip.append(ovirtmgmt_ip)
    return vms_ovirtmgmt_ip


@pytest.fixture(scope='module')
def vm_nodes(vms_ovirtmgmt_ip):
    return (sshlib.CirrosNode(vms_ovirtmgmt_ip[0], VM_PASSWORD, VM_USERNAME),
            sshlib.CirrosNode(vms_ovirtmgmt_ip[1], VM_PASSWORD, VM_USERNAME))


@pytest.fixture(scope='module')
def isolated_vnics_up_with_ip(vm_nodes):
    ips = []
    for vm_node in vm_nodes:
        vm_node.assign_ip_with_dhcp_client(PORT_ISOLATED_VNIC)
        ip = vm_node.get_ipv4_of_interface(PORT_ISOLATED_VNIC)
        ips.append(ip)
    return ips


@pytest.fixture(scope='module')
def vms_up_on_same_host(system, default_cluster, cirros_template,
                        port_isolation_network, ovirtmgmt_vnic_profile):
    """
    Since the isolated_network is set up only on one host,
    both virtual machines will be on the same host.
    """
    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vms = [(vm_0, VM0_NAME),
               (vm_1, VM1_NAME)
               ]
        for vm, name in vms:
            vm.create(
                vm_name=name,
                cluster=default_cluster,
                template=cirros_template
            )
            vm_vnic0 = netlib.Vnic(vm)
            vm_vnic0.create(
                name=VNIC0_NAME,
                vnic_profile=ovirtmgmt_vnic_profile,
            )
            vm_vnic1 = netlib.Vnic(vm)
            vm_vnic1.create(
                name=PORT_ISOLATED_VNIC,
                vnic_profile=port_isolation_network.vnic_profile(),
            )
            vm.wait_for_down_status()
            vm.run_once(cloud_init_hostname=name)

        vm_0.wait_for_up_status()
        vm_1.wait_for_up_status()
        joblib.AllJobs(system).wait_for_done()
        yield


@pytest.fixture(scope='module')
def port_isolation_network(default_data_center, default_cluster, host_1_up):
    with clusterlib.new_assigned_network(
        PORT_ISOLATION_NET, default_data_center, default_cluster,
        port_isolation=True
    ) as network:
        attach_data = netattachlib.NetworkAttachmentData(network, ETH1)
        with hostlib.setup_networks(host_1_up, attach_data=(attach_data,)):
            yield network


class PingSucceededException(Exception):
    pass
