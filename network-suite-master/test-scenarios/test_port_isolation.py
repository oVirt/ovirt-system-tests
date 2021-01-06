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

from ovirtlib import clusterlib
from ovirtlib import hostlib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import sshlib
from ovirtlib import virtlib


ETH1 = 'eth1'
VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
VNIC0_NAME = 'eth1'
VNIC1_NAME = 'eth2'
PORT_ISOLATION_NET = 'test_isolated'
VM_USERNAME = 'cirros'
VM_PASSWORD = 'gocubsgo'
PING_FAILED = '100% packet loss'


def test_ping_to_external_port_succeeds(vms_ovirtmgmt_ip):
    for ip in vms_ovirtmgmt_ip:
        vm_node = sshlib.Node(ip, VM_PASSWORD, VM_USERNAME)
        vm_node.ping4('8.8.8.8', ETH1)


def test_ping_to_isolated_port_fails(vms_ovirtmgmt_ip):
    vm_node0 = sshlib.Node(vms_ovirtmgmt_ip[0], VM_PASSWORD, VM_USERNAME)
    vm_node1 = sshlib.Node(vms_ovirtmgmt_ip[1], VM_PASSWORD, VM_USERNAME)
    vm1_port_isolated_ip = vm_node1.get_ipv4_of_interface(ETH1)
    try:
        vm_node0.ping4(vm1_port_isolated_ip, ETH1)
        raise PingSucceededException
    except sshlib.SshException as err:
        if PING_FAILED not in str(err):
            raise


@pytest.fixture(scope='module')
def vms_ovirtmgmt_ip(host_1_up, vms_up_on_same_host):
    vms_ovirtmgmt_ip = []
    host_node = sshlib.Node(host_1_up.address, host_1_up.root_password)
    for name in [VM0_NAME, VM1_NAME]:
        ovirtmgmt_ip = host_node.lookup_ip_address_with_dns_query(name)
        vm_node = sshlib.CirrosNode(ovirtmgmt_ip, VM_PASSWORD, VM_USERNAME)
        vm_node.assign_ip_with_dhcp_client(ETH1)
        vms_ovirtmgmt_ip.append(ovirtmgmt_ip)
    yield vms_ovirtmgmt_ip


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
                name=VNIC1_NAME,
                vnic_profile=port_isolation_network.vnic_profile(),
            )
            vm.wait_for_down_status()
            vm.run_once(cloud_init_hostname=name)

        vm_0.wait_for_up_status()
        vm_1.wait_for_up_status()
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
