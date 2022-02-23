#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from contextlib import contextmanager
import os

import pytest

from ovirtlib.ansiblelib import Playbook
from ovirtlib import sshlib
from testlib import suite


NETWORK10_NAME = 'net10'
ROUTER0_NAME = 'router0'
ROUTER1_NAME = 'router1'


class HostConfigurationFailure(Exception):
    pass


class OvnNetwork(object):
    def __init__(self, port_name, subnet_name, ovn_provider_client):
        self._port = ovn_provider_client.get_port(port_name)
        self._subnet = ovn_provider_client.get_subnet(subnet_name)

    @property
    def port(self):
        return self._port

    @property
    def ip(self):
        return self._port.fixed_ips[0]['ip_address']

    @property
    def subnet(self):
        return self._subnet


def test_ovn_provider_create_scenario(openstack_client_config, af):
    scenario = {
        'inet': 'create_scenario.yml',
        'inet6': 'create_scenario_ipv6.yml',
    }
    _test_ovn_provider(scenario[af.family])


def test_validate_ovn_provider_connectivity(default_ovn_provider_client, host_0, host_1, ovn_networks, af):
    net10, net11, net14 = ovn_networks
    ssh0 = sshlib.Node(host_0.address, host_0.root_password)
    ssh1 = sshlib.Node(host_1.address, host_1.root_password)

    connections = (
        (ssh0, net10),
        (ssh1, net11),
        (ssh1, net14),
    )
    with _create_namespaces(connections):
        with _create_ovs_ports(connections, af):
            ssh0.assert_ping_from_netns(net11.ip, net10.port.name)
            ssh1.assert_ping_from_netns(net10.ip, net11.port.name)

            ssh0.assert_no_ping_from_netns(net14.ip, net10.port.name)
            ssh1.assert_no_ping_from_netns(net10.ip, net14.port.name)

            _update_routes(default_ovn_provider_client, net10.subnet, net11.subnet)

            ssh1.assert_ping_from_netns(net10.ip, net14.port.name)
            ssh0.assert_ping_from_netns(net14.ip, net10.port.name)
            ssh1.assert_ping_from_netns(net11.ip, net14.port.name)
            ssh1.assert_ping_from_netns(net14.ip, net11.port.name)


@pytest.fixture(scope='function')
def ovn_networks(default_ovn_provider_client):
    client = default_ovn_provider_client
    net10 = OvnNetwork('net10_port1', 'net10_subnet1', client)
    net11 = OvnNetwork('net11_port1', 'net11_subnet1', client)
    net14 = OvnNetwork('net14_port1', 'net14_subnet1', client)
    return net10, net11, net14


def _update_routes(default_ovn_provider_client, net10_subnet1, net11_subnet1):
    router0 = default_ovn_provider_client.get_router(ROUTER0_NAME)
    router1 = default_ovn_provider_client.get_router(ROUTER1_NAME)

    nexthop = router0.external_gateway_info['external_fixed_ips'][0]['ip_address']
    default_ovn_provider_client.update_router(
        router1.id, routes=[_define_static_route(nexthop, net10_subnet1), _define_static_route(nexthop, net11_subnet1)]
    )


def _define_static_route(nexthop, subnet):
    return {'nexthop': nexthop, 'destination': subnet.cidr}


def test_ovn_provider_cleanup_scenario(openstack_client_config):
    _test_ovn_provider('cleanup_scenario.yml')


def _test_ovn_provider(playbook_name):
    playbook_path = os.path.join(suite.playbook_dir(), playbook_name)
    playbook = Playbook(playbook_path)
    playbook.run()

    assert not playbook.execution_stats['failures']
    assert not playbook.idempotency_check_stats['failures']
    assert playbook.execution_stats['changed'].get('localhost', 0) > 0
    assert not playbook.idempotency_check_stats['changed']


@contextmanager
def _create_namespaces(connections):
    try:
        for ssh_host, net in connections:
            ssh_host.exec_command(_add_namespace_command(net.port.name))
        yield
    finally:
        for ssh_host, net in connections:
            ssh_host.exec_command(_delete_namespace_command(net.port.name))


@contextmanager
def _create_ovs_ports(connections, af):
    try:
        for ssh_host, net in connections:
            ssh_host.exec_command(_configure_ovs_port_command(net.port, net.subnet, af))
        yield
    finally:
        for ssh_host, net in connections:
            ssh_host.exec_command(_delete_ovs_port_command(net.port.name))


def _add_namespace_command(name):
    return f'ip netns add {name}'


def _delete_namespace_command(name):
    return f'ip netns delete {name}'


def _configure_ovs_port_command(port, subnet, af):
    ip = port.fixed_ips[0]['ip_address']
    prefix = '64' if af.is6 else '24'
    commands = [
        f'ovs-vsctl add-port br-int {port.name} -- set interface {port.name} type=internal',
        f'ip link set {port.name} netns {port.name}',
        f'ip netns exec {port.name} ip link set {port.name} address {port.mac_address}',
        f'ip netns exec {port.name} ip a add {ip}/{prefix} dev {port.name}',
        f'ip netns exec {port.name} ip link set {port.name} up',
        f'ip netns exec {port.name} ip route add default via {subnet.gateway_ip}',
        f'ovs-vsctl set Interface {port.name} external_ids:iface-id={port.id}',
    ]
    return ' && '.join(commands)


def _delete_ovs_port_command(name):
    return f'ovs-vsctl del-port {name}'
