#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from collections import namedtuple
import logging
import pytest

from fixtures.host import ETH1

from ovirtlib import clusterlib
from ovirtlib import hostlib
from ovirtlib import joblib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import sshlib
from ovirtlib import virtlib


PORT_ISOLATION_NET = 'test_port_isolation_net'
VM_USERNAME = 'cirros'
VM_PASSWORD = 'gocubsgo'
PING_FAILED = '100% packet loss'
EXTERNAL_IP = {'inet': '8.8.8.8', 'inet6': '2001:4860:4860::8888'}
Iface = namedtuple('Iface', ['name', 'ipv6'])
VmConf = namedtuple('Vmconf', ['name', 'mgmt_iface', 'isolated_iface'])

LOGGER = logging.getLogger(__name__)


def test_ping_to_external_port_succeeds(vm_nodes, vms_conf, isolated_ifaces_up_with_ip, af, request):
    if af.is6:
        request.node.add_marker(pytest.mark.xfail(reason='CI lab does not provide external ipv6 connectivity'))
    for i, vm_node in enumerate(vm_nodes):
        vm_node.ping(EXTERNAL_IP[af.family], af.version, vms_conf[i].isolated_iface.name)


def test_ping_to_mgmt_port_succeeds(vm_nodes, vms_conf, mgmt_ifaces_up_with_ip, af):
    vm_nodes[0].ping(mgmt_ifaces_up_with_ip[1], af.version, vms_conf[0].mgmt_iface.name)
    vm_nodes[1].ping(mgmt_ifaces_up_with_ip[0], af.version, vms_conf[1].mgmt_iface.name)


def test_ping_to_isolated_port_fails(vm_nodes, isolated_ifaces_up_with_ip, af):
    with pytest.raises(sshlib.SshException, match=PING_FAILED):
        vm_nodes[0].ping(isolated_ifaces_up_with_ip[1], af.version)
    with pytest.raises(sshlib.SshException, match=PING_FAILED):
        vm_nodes[1].ping(isolated_ifaces_up_with_ip[0], af.version)


@pytest.fixture(scope='module')
def vms_conf(management_subnet, storage_subnet):
    return [
        VmConf(
            'test_port_isolation_vm_0',
            Iface('eth0', str(management_subnet[221])),
            Iface('eth1', str(storage_subnet[221])),
        ),
        VmConf(
            'test_port_isolation_vm_1',
            Iface('eth0', str(management_subnet[222])),
            Iface('eth1', str(storage_subnet[222])),
        ),
    ]


@pytest.fixture(scope='module')
def vm_nodes(mgmt_ifaces_up_with_ip):
    return (
        sshlib.Node(mgmt_ifaces_up_with_ip[0], VM_PASSWORD, VM_USERNAME),
        sshlib.Node(mgmt_ifaces_up_with_ip[1], VM_PASSWORD, VM_USERNAME),
    )


@pytest.fixture(scope='module')
def mgmt_ifaces_up_with_ip(vms_up_on_host_1, vms_conf, cirros_serial_console, af):
    return _assign_ips_on_vms_ifaces(
        vms_up_on_host_1, cirros_serial_console, (vms_conf[0].mgmt_iface, vms_conf[1].mgmt_iface), af
    )


@pytest.fixture(scope='module')
def isolated_ifaces_up_with_ip(vms_up_on_host_1, vms_conf, cirros_serial_console, af):
    return _assign_ips_on_vms_ifaces(
        vms_up_on_host_1, cirros_serial_console, (vms_conf[0].isolated_iface, vms_conf[1].isolated_iface), af
    )


def _assign_ips_on_vms_ifaces(vms, serial_console, ifaces, af):
    ips = []
    for i, vm in enumerate(vms):
        name = ifaces[i].name
        if af.is6:
            ipv6 = ifaces[i].ipv6
            ip = serial_console.add_static_ip(vm.id, f'{ipv6}/128', name)
        else:
            ip = serial_console.assign_ip4_if_missing(vm.id, name)
        LOGGER.debug(f'after applying ips: vm={vm.name} has {ip} on {name}')
        ips.append(ip)
    return ips


@pytest.fixture(scope='module')
def vms_up_on_host_1(
    system,
    default_cluster,
    cirros_template,
    port_isolation_network,
    ovirtmgmt_vnic_profile,
    cirros_serial_console,
    vms_conf,
):
    """
    Since the isolated_network is set up only on host_1,
    both virtual machines will be on it.
    """
    with virtlib.vm_pool(system, size=2) as (vm_0, vm_1):
        for i, vm in enumerate([vm_0, vm_1]):
            vm.create(vm_name=vms_conf[i].name, cluster=default_cluster, template=cirros_template)
            vm_vnic0 = netlib.Vnic(vm)
            vm_vnic0.create(name=vms_conf[i].mgmt_iface.name, vnic_profile=ovirtmgmt_vnic_profile)

            vm_vnic1 = netlib.Vnic(vm)
            vm_vnic1.create(name=vms_conf[i].isolated_iface.name, vnic_profile=port_isolation_network.vnic_profile())
            vm.wait_for_down_status()
            vm.run_once(cloud_init_hostname=vms_conf[i].name)

        vm_0.wait_for_up_status()
        vm_1.wait_for_up_status()
        joblib.AllJobs(system).wait_for_done()
        for vm in (vm_0, vm_1):
            ip_a = cirros_serial_console.shell(vm.id, ('ip addr',))
            LOGGER.debug(f'before applying ips: vm={vm.name} has ip_a={ip_a}')
        yield vm_0, vm_1


@pytest.fixture(scope='module')
def port_isolation_network(default_data_center, default_cluster, host_1_up, af):
    with clusterlib.new_assigned_network(
        PORT_ISOLATION_NET,
        default_data_center,
        default_cluster,
        port_isolation=True,
    ) as network:
        attach_data = netattachlib.NetworkAttachmentData(network, ETH1, (netattachlib.DYNAMIC_IP_ASSIGN[af.family],))
        with hostlib.setup_networks(host_1_up, attach_data=(attach_data,)):
            yield network
