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
from contextlib import contextmanager
import os

from lib.ansiblelib import Playbook
from lib import sshlib as ssh
from testlib import shade_hack
from testlib import suite


PLAYBOOK_DIR = os.path.join(os.environ.get('SUITE'), 'ansible')
NETWORK10_NAME = 'net10'
NETWORK10_PORT1_NAME = 'net10_port1'
NETWORK11_PORT1_NAME = 'net11_port1'
NETWORK10_SUBNET1_NAME = 'net10_subnet1'
NETWORK11_SUBNET1_NAME = 'net11_subnet1'


pytestmark = suite.SKIP_SUITE_42


class HostConfigurationFailure(Exception):
    pass


def test_ovn_provider_create_scenario(openstack_client_config):
    _test_ovn_provider('create_scenario.yml')


def test_validate_ovn_provider_connectivity(default_ovn_provider_client,
                                            host_0, host_1):
    port1 = default_ovn_provider_client.get_port(NETWORK10_PORT1_NAME)
    port2 = default_ovn_provider_client.get_port(NETWORK11_PORT1_NAME)

    subnet1 = default_ovn_provider_client.get_subnet(NETWORK10_SUBNET1_NAME)
    subnet2 = default_ovn_provider_client.get_subnet(NETWORK11_SUBNET1_NAME)

    connections = ((host_0, port1, subnet1,), (host_1, port2, subnet2,),)
    with _create_namespaces(connections):
        with _create_ovs_ports(connections):
            ssh.exec_command(host_0.address, host_0.root_password,
                             'ip netns exec ' + port1.name + ' ping -4 -c 1 ' +
                             port2.fixed_ips[0]['ip_address'])

            ssh.exec_command(host_1.address, host_1.root_password,
                             'ip netns exec ' + port2.name + ' ping -4 -c 1 ' +
                             port1.fixed_ips[0]['ip_address'])


def test_update_network_mtu(default_ovn_provider_client):
    network10 = default_ovn_provider_client.get_network(NETWORK10_NAME)
    mtu = 1501
    path = '/networks/{network_id}'.format(network_id=network10.id)
    data = {'network': {'mtu': mtu, 'name': network10.name}}

    # HACK: this is a workaround until BZ 1590248 and BZ 1590251 are fixed
    shade_hack.hack_os_put_request(default_ovn_provider_client, path, data)

    network10 = default_ovn_provider_client.get_network(NETWORK10_NAME)
    assert network10.mtu == mtu


def test_ovn_provider_cleanup_scenario(openstack_client_config):
    _test_ovn_provider('cleanup_scenario.yml')


def _test_ovn_provider(playbook_name):
    playbook_path = os.path.join(PLAYBOOK_DIR, playbook_name)
    playbook = Playbook([playbook_path])
    playbook.run()

    assert not playbook.execution_stats.failures
    assert not playbook.idempotency_check_stats.failures
    assert playbook.execution_stats.changed.get('localhost', 0) > 0
    assert not playbook.idempotency_check_stats.changed


@contextmanager
def _create_namespaces(connections):
    namespaces = list()
    try:
        for host, port, _ in connections:
            _exec(host, _add_namespace_command(port.name))
            namespaces.append((host, port.name))
        yield
    finally:
        for host, name in namespaces:
            _exec(host, _delete_namespace_command(name))


@contextmanager
def _create_ovs_ports(connections):
    ports = list()
    try:
        for host, port, _ in connections:
            _exec(host, _add_ovs_port_command(port.name))
            ports.append((host, port.name))
        for host, port, subnet in connections:
            _exec(host, _configure_ovs_port_command(port, subnet) +
                  _bind_port_to_logical_network(port))
        yield
    finally:
        for host, name in ports:
            _exec(host, _delete_ovs_port_command(name))


def _exec(host, commands):
    ssh.exec_command(host.address, host.root_password,
                     ' && '.join(commands))


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
