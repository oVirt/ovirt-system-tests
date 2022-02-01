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
from testlib import shade_hack
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
    if af.is6:
        pytest.xfail(reason='fails with ansible runner on executor gerrit 118275')
    net10, net11, net14 = ovn_networks
    ssh0 = sshlib.Node(host_0.address, host_0.root_password)
    ssh1 = sshlib.Node(host_1.address, host_1.root_password)

    connections = (
        (
            ssh0,
            net10.port,
            net10.subnet,
        ),
        (
            ssh1,
            net11.port,
            net11.subnet,
        ),
        (
            ssh1,
            net14.port,
            net14.subnet,
        ),
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


# HACK: this is a workaround until BZ 1593643 and BZ 1593648 are fixed
# once the bugs are fixed, this should be moved over to ansible
def _update_routes(default_ovn_provider_client, net10_subnet1, net11_subnet1):
    router0 = default_ovn_provider_client.get_router(ROUTER0_NAME)
    router1 = default_ovn_provider_client.get_router(ROUTER1_NAME)

    router0_external_ip = router0.external_gateway_info['external_fixed_ips'][0]['ip_address']

    router1_path = '/routers/{router_id}'.format(router_id=router1.id)
    routes_put_data = _static_routes_request_data(router1.name, router0_external_ip, net10_subnet1, net11_subnet1)

    shade_hack.hack_os_put_request(default_ovn_provider_client, router1_path, routes_put_data)


def _define_static_route(nexthop, subnet):
    return {'nexthop': nexthop, 'destination': subnet.cidr}


def _static_routes_request_data(router_name, nexthop, net10_subnet1, net11_subnet1):
    return {
        'router': {
            'name': router_name,
            'routes': [
                _define_static_route(nexthop, net10_subnet1),
                _define_static_route(nexthop, net11_subnet1),
            ],
        }
    }


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
    namespaces = list()
    try:
        for ssh_host, port, _ in connections:
            ssh_host.exec_command(' && '.join(_add_namespace_command(port.name)))
            namespaces.append((ssh_host, port.name))
        yield
    finally:
        for ssh_host, name in namespaces:
            ssh_host.exec_command(' && '.join(_delete_namespace_command(name)))


@contextmanager
def _create_ovs_ports(connections, af):
    ports = list()
    try:
        for ssh_host, port, _ in connections:
            ssh_host.exec_command(' && '.join(_add_ovs_port_command(port.name)))
            ports.append((ssh_host, port.name))
        for ssh_host, port, subnet in connections:
            ssh_host.exec_command(
                ' && '.join(_configure_ovs_port_command(port, subnet, af) + _bind_port_to_logical_network(port))
            )
        yield
    finally:
        for ssh_host, name in ports:
            ssh_host.exec_command(' && '.join(_delete_ovs_port_command(name)))


def _add_namespace_command(name):
    return ['ip netns add ' + name]


def _add_ovs_port_command(name):
    commands = ['ovs-vsctl add-port br-int ' + name + ' -- set interface ' + name + ' type=internal']
    return commands


def _configure_ovs_port_command(port, subnet, af):
    name = port.name
    ip = port.fixed_ips[0]['ip_address']
    mac = port.mac_address
    gw = subnet.gateway_ip
    prefix = '64' if af.is6 else '24'
    commands = [
        'ip link set ' + name + ' netns ' + name,
        'ip netns exec ' + name + ' ip link set ' + name + ' address ' + mac,
        'ip netns exec ' + name + ' ip a add ' + ip + f'/{prefix} dev ' + name,
        'ip netns exec ' + name + ' ip link set ' + name + ' up',
        'ip netns exec ' + name + ' ip route add default via ' + gw,
    ]
    return commands


def _bind_port_to_logical_network(port):
    return ['ovs-vsctl set Interface ' + port.name + ' external_ids:iface-id=' + port.id]


def _delete_namespace_command(name):
    return ['ip netns delete ' + name]


def _delete_ovs_port_command(name):
    return ['ovs-vsctl del-port ' + name]
