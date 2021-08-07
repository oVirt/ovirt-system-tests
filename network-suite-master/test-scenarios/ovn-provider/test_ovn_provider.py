#
# Copyright 2018-2021 Red Hat, Inc.
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
from contextlib import contextmanager
import os

import pytest

from ovirtlib.ansiblelib import Playbook
from ovirtlib import sshlib
from testlib.ping import PingFailed
from testlib.ping import ssh_ping
from testlib import shade_hack
from testlib import suite


NETWORK10_NAME = 'net10'
NETWORK10_PORT1_NAME = 'net10_port1'
NETWORK11_PORT1_NAME = 'net11_port1'
NETWORK14_PORT1_NAME = 'net14_port1'
NETWORK10_SUBNET1_NAME = 'net10_subnet1'
NETWORK11_SUBNET1_NAME = 'net11_subnet1'
NETWORK14_SUBNET1_NAME = 'net14_subnet1'
ROUTER0_NAME = 'router0'
ROUTER1_NAME = 'router1'


class HostConfigurationFailure(Exception):
    pass


def test_ovn_provider_create_scenario(openstack_client_config):
    _test_ovn_provider('create_scenario.yml')


def test_validate_ovn_provider_connectivity(default_ovn_provider_client,
                                            host_0, host_1):
    net10_port1 = default_ovn_provider_client.get_port(NETWORK10_PORT1_NAME)
    net11_port1 = default_ovn_provider_client.get_port(NETWORK11_PORT1_NAME)
    net14_port1 = default_ovn_provider_client.get_port(NETWORK14_PORT1_NAME)

    net10_subnet1 = default_ovn_provider_client.get_subnet(
        NETWORK10_SUBNET1_NAME)
    net11_subnet1 = default_ovn_provider_client.get_subnet(
        NETWORK11_SUBNET1_NAME)
    net14_subnet1 = default_ovn_provider_client.get_subnet(
        NETWORK14_SUBNET1_NAME)

    connections = (
        (host_0, net10_port1, net10_subnet1,),
        (host_1, net11_port1, net11_subnet1,),
        (host_1, net14_port1, net14_subnet1,)
    )
    with _create_namespaces(connections):
        with _create_ovs_ports(connections):
            assert_connectivity_between(host=host_0, from_port=net10_port1,
                                        to_port=net11_port1)
            assert_connectivity_between(host=host_1, from_port=net11_port1,
                                        to_port=net10_port1)

            assert_no_connectivity_between(host=host_0, from_port=net10_port1,
                                           to_port=net14_port1)
            assert_no_connectivity_between(host=host_1, from_port=net14_port1,
                                           to_port=net10_port1)

            _update_routes(default_ovn_provider_client, net10_subnet1,
                           net11_subnet1)

            assert_connectivity_between(host=host_1, from_port=net14_port1,
                                        to_port=net10_port1)
            assert_connectivity_between(host=host_0, from_port=net10_port1,
                                        to_port=net14_port1)
            assert_connectivity_between(host=host_1, from_port=net14_port1,
                                        to_port=net11_port1)
            assert_connectivity_between(host=host_1, from_port=net11_port1,
                                        to_port=net14_port1)


def assert_connectivity_between(host, from_port, to_port):
    _ping(host=host, from_port=from_port, to_port=to_port)


def assert_no_connectivity_between(host, from_port, to_port):
    with pytest.raises(PingFailed):
        ssh_ping(source=host.address, password=host.root_password,
                 destination=to_port.fixed_ips[0]['ip_address'],
                 netns=from_port.name)


def _ping(host, from_port, to_port):
    ssh_ping(source=host.address, password=host.root_password,
             destination=to_port.fixed_ips[0]['ip_address'],
             netns=from_port.name)


# HACK: this is a workaround until BZ 1593643 and BZ 1593648 are fixed
# once the bugs are fixed, this should be moved over to ansible
def _update_routes(default_ovn_provider_client, net10_subnet1, net11_subnet1):
    router0 = default_ovn_provider_client.get_router(ROUTER0_NAME)
    router1 = default_ovn_provider_client.get_router(ROUTER1_NAME)

    router0_external_ip = router0.external_gateway_info[
        'external_fixed_ips'][0]['ip_address']

    router1_path = '/routers/{router_id}'.format(router_id=router1.id)
    routes_put_data = _static_routes_request_data(
        router1.name, router0_external_ip, net10_subnet1, net11_subnet1)

    shade_hack.hack_os_put_request(
        default_ovn_provider_client, router1_path, routes_put_data)


def _define_static_route(nexthop, subnet):
    return {
        'nexthop': nexthop,
        'destination': subnet.cidr
    }


def _static_routes_request_data(router_name, nexthop, net10_subnet1,
                                net11_subnet1):
    return {'router': {
        'name': router_name,
        'routes': [
            _define_static_route(nexthop, net10_subnet1),
            _define_static_route(nexthop, net11_subnet1)
        ]
    }}


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
        for host, port, _ in connections:
            sshlib.Node(host.address, host.root_password).exec_command(
                ' && '.join(_add_namespace_command(port.name)))
            namespaces.append((host, port.name))
        yield
    finally:
        for host, name in namespaces:
            sshlib.Node(host.address, host.root_password).exec_command(
                ' && '.join(_delete_namespace_command(name)))


@contextmanager
def _create_ovs_ports(connections):
    ports = list()
    try:
        for host, port, _ in connections:
            sshlib.Node(host.address, host.root_password).exec_command(
                ' && '.join(_add_ovs_port_command(port.name)))
            ports.append((host, port.name))
        for host, port, subnet in connections:
            sshlib.Node(host.address, host.root_password).exec_command(
                ' && '.join(
                    _configure_ovs_port_command(port, subnet) +
                    _bind_port_to_logical_network(port)
                )
            )
        yield
    finally:
        for host, name in ports:
            sshlib.Node(host.address, host.root_password).exec_command(
                ' && '.join(_delete_ovs_port_command(name)))


def _add_namespace_command(name):
    return ['ip netns add ' + name]


def _add_ovs_port_command(name):
    commands = [
        'ovs-vsctl add-port br-int ' + name + ' -- set interface ' + name +
        ' type=internal'
    ]
    return commands


def _configure_ovs_port_command(port, subnet):
    name = port.name
    ip = port.fixed_ips[0]['ip_address']
    mac = port.mac_address
    gw = subnet.gateway_ip
    commands = [
        'ip link set ' + name + ' netns ' + name,
        'ip netns exec ' + name + ' ip link set ' + name + ' address ' + mac,
        'ip netns exec ' + name + ' ip addr add ' + ip + '/24 dev ' + name,
        'ip netns exec ' + name + ' ip link set ' + name + ' up',
        'ip netns exec ' + name + ' ip route add default via ' + gw,
    ]
    return commands


def _bind_port_to_logical_network(port):
    return ['ovs-vsctl set Interface ' + port.name +
            ' external_ids:iface-id=' + port.id]


def _delete_namespace_command(name):
    return ['ip netns delete ' + name]


def _delete_ovs_port_command(name):
    return ['ovs-vsctl del-port ' + name]
