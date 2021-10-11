#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from collections import namedtuple
import pytest

from fixtures.host import ETH1

from ovirtlib import clusterlib
from ovirtlib import hostlib
from ovirtlib import joblib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import sshlib
from ovirtlib import virtlib

from testlib import suite

VM0_NAME = 'test_port_isolation_vm_0'
VM1_NAME = 'test_port_isolation_vm_1'
PORT_ISOLATION_NET = 'test_port_isolation_net'
VM_USERNAME = 'cirros'
VM_PASSWORD = 'gocubsgo'
PING_FAILED = '100% packet loss'
EXTERNAL_IP = {'inet': '8.8.8.8', 'inet6': '2001:4860:4860::8888'}
Iface = namedtuple('Iface', ['name', 'ipv6'])
IFACE_0 = Iface('eth0', 'fd8f:1391:3a82:200::cafe:e0')
IFACE_ISOLATED = Iface('eth1', 'fd8f:1391:3a82:201::cafe:e1')


@pytest.mark.xfail(
    suite.af().is6, reason='CI lab does not provide external ipv6 connectivity'
)
def test_ping_to_external_port_succeeds(vm_nodes, isolated_ifaces_up_with_ip):
    for vm_node in vm_nodes:
        vm_node.ping(EXTERNAL_IP[suite.af().family], IFACE_ISOLATED.name)


def test_ping_to_isolated_port_fails(vm_nodes, isolated_ifaces_up_with_ip):
    with pytest.raises(sshlib.SshException, match=PING_FAILED):
        vm_nodes[0].ping(isolated_ifaces_up_with_ip[1], IFACE_ISOLATED.name)
    with pytest.raises(sshlib.SshException, match=PING_FAILED):
        vm_nodes[1].ping(isolated_ifaces_up_with_ip[0], IFACE_ISOLATED.name)


@pytest.fixture(scope='module')
def vms_ovirtmgmt_ip(host_1_up, vms_up_on_host_1, cirros_serial_console):
    vms_ovirtmgmt_ip = []
    for vm in vms_up_on_host_1:
        if suite.af().is6:
            ip = IFACE_0.ipv6
            cirros_serial_console.add_static_ip(
                vm.id, f'{ip}/64', IFACE_0.name
            )
        else:
            host_node = sshlib.Node(host_1_up.address, host_1_up.root_password)
            ip = host_node.lookup_ip_address_with_dns_query(
                vm.name, suite.af().version
            )
        vms_ovirtmgmt_ip.append(ip)
    return vms_ovirtmgmt_ip


@pytest.fixture(scope='module')
def vm_nodes(vms_ovirtmgmt_ip):
    return (
        sshlib.CirrosNode(vms_ovirtmgmt_ip[0], VM_PASSWORD, VM_USERNAME),
        sshlib.CirrosNode(vms_ovirtmgmt_ip[1], VM_PASSWORD, VM_USERNAME),
    )


@pytest.fixture(scope='module')
def isolated_ifaces_up_with_ip(
    vm_nodes, vms_up_on_host_1, cirros_serial_console
):
    if suite.af().is6:
        return isolated_ifaces_up_with_ipv6(
            vms_up_on_host_1, cirros_serial_console
        )
    else:
        return isolated_ifaces_up_with_ipv4(vm_nodes)


def isolated_ifaces_up_with_ipv6(vms_up_on_host_1, cirros_serial_console):
    ips = []
    for vm in vms_up_on_host_1:
        ip = IFACE_ISOLATED.ipv6
        cirros_serial_console.add_static_ip(
            vm.id, f'{ip}/64', IFACE_ISOLATED.name
        )
        ips.append(ip)
    return ips


def isolated_ifaces_up_with_ipv4(vm_nodes):
    ips = []
    for vm_node in vm_nodes:
        vm_node.assign_ip_with_dhcp_client(IFACE_ISOLATED.name)
        ip = vm_node.get_global_ip(IFACE_ISOLATED.name, suite.af().version)
        ips.append(ip)
    return ips


@pytest.fixture(scope='module')
def vms_up_on_host_1(
    system,
    default_cluster,
    cirros_template,
    port_isolation_network,
    ovirtmgmt_vnic_profile,
):
    """
    Since the isolated_network is set up only on host_1,
    both virtual machines will be on it.
    """
    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        vms = [(vm_0, VM0_NAME), (vm_1, VM1_NAME)]
        for vm, name in vms:
            vm.create(
                vm_name=name, cluster=default_cluster, template=cirros_template
            )
            vm_vnic0 = netlib.Vnic(vm)
            vm_vnic0.create(
                name=IFACE_0.name,
                vnic_profile=ovirtmgmt_vnic_profile,
            )
            vm_vnic1 = netlib.Vnic(vm)
            vm_vnic1.create(
                name=IFACE_ISOLATED.name,
                vnic_profile=port_isolation_network.vnic_profile(),
            )
            vm.wait_for_down_status()
            vm.run_once(cloud_init_hostname=name)

        vm_0.wait_for_up_status()
        vm_1.wait_for_up_status()
        joblib.AllJobs(system).wait_for_done()
        yield vm_0, vm_1


@pytest.fixture(scope='module')
def port_isolation_network(default_data_center, default_cluster, host_1_up):
    with clusterlib.new_assigned_network(
        PORT_ISOLATION_NET,
        default_data_center,
        default_cluster,
        port_isolation=True,
    ) as network:
        attach_data = netattachlib.NetworkAttachmentData(
            network, ETH1, (netattachlib.DYNAMIC_IP_ASSIGN[suite.af().family],)
        )
        with hostlib.setup_networks(host_1_up, attach_data=(attach_data,)):
            yield network
