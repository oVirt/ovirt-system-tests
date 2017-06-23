#
# Copyright 2017 Red Hat, Inc.
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

import copy
import requests
import urlparse

import nose.tools as nt

from ovirtlago import testlib


OVN_PROVIDER_TOKEN_URL = 'https://{hostname}:35357/v2.0/tokens/'
OVN_PROVIDER_NETWORKS_URL = 'https://{hostname}:9696/v2.0/networks/'
OVN_PROVIDER_PORTS_URL = 'https://{hostname}:9696/v2.0/ports/'
OVN_PROVIDER_SUBNETS_URL = 'https://{hostname}:9696/v2.0/subnets/'

OVIRT_USER = 'admin@internal'
OVIRT_PASSWORD = '123'

NETWORK_1 = 'network_1'
PORT_1 = 'port_1'
SUBNET_1 = 'subnet_1'

NETWORKS = {
    NETWORK_1: {
        'name': NETWORK_1

    }
}

PORTS = {
    PORT_1: {
        'name': PORT_1,
        'admin_state_up': True,
        'device_id': 'port_1_device_id',
        'device_owner': 'ovirt',
        'mac_address': 'de:ad:ca:fe:ba:be',
    }
}

SUBNETS = {
    SUBNET_1: {
        'name': SUBNET_1,
        'dns_nameservers': ["8.8.8.8"],
        'gateway_ip': '1.1.1.1',
        'cidr': '1.1.1.0/24'
    }

}


def _request_auth_token(engine_name):
    auth_request_data = {
        'auth': {
            'tenantName': 'ovirt-provider-ovn',
            'passwordCredentials': {
                'username': OVIRT_USER,
                'password': OVIRT_PASSWORD
            }
        }
    }
    response = requests.post(
        OVN_PROVIDER_TOKEN_URL.format(
            hostname=engine_name
        ),
        json=auth_request_data,
        verify=False)
    return response.json()


def _get_auth_token(engine_name):
    response_json = _request_auth_token(engine_name)
    token_id = response_json['access']['token']['id']
    return token_id


def _send_get(token_id, url):
    response = requests.get(
        url,
        verify=False,
        headers={
            'X-Auth-Token': token_id
        },
    )
    return response.json()


def _send_post(token_id, url, data):
    response = requests.post(
        url,
        verify=False,
        headers={
            'X-Auth-Token': token_id
        },
        json=data,
    )
    return response.json()


def _send_delete(token_id, url, id):
    requests.delete(
        urlparse.urljoin(url, id),
        verify=False,
        headers={
            'X-Auth-Token': token_id
        },
    )


def _get_networks(token_id, engine_name):
    return _send_get(
        token_id,
        OVN_PROVIDER_NETWORKS_URL.format(hostname=engine_name),
    )


def _get_ports(token_id, engine_name):
    return _send_get(
        token_id,
        OVN_PROVIDER_PORTS_URL.format(hostname=engine_name),
    )


def _get_subnets(token_id, engine_name):
    return _send_get(
        token_id,
        OVN_PROVIDER_SUBNETS_URL.format(hostname=engine_name),
    )


def _add_network(token_id, engine_name, name):
    network_data = copy.copy(NETWORKS[name])
    network = _send_post(
        token_id,
        OVN_PROVIDER_NETWORKS_URL.format(hostname=engine_name),
        data={
            "network": network_data
        }
    )
    return str(network['network']['id'])


def _add_subnet(
    token_id,
    engine_name,
    name,
    network_id,
):
    subnet_data = copy.copy(SUBNETS[name])
    subnet_data['network_id'] = network_id
    subnet = _send_post(
        token_id,
        OVN_PROVIDER_SUBNETS_URL.format(hostname=engine_name),
        data={
            'subnet': subnet_data
        }
    )
    return str(subnet['subnet']['id'])


def _add_port(
    token_id,
    engine_name,
    name,
    network_id,
):
    port_data = copy.copy(PORTS[name])
    port_data['network_id'] = network_id
    port = _send_post(
        token_id,
        OVN_PROVIDER_PORTS_URL.format(hostname=engine_name),
        data={
            'port': port_data
        }
    )
    return str(port['port']['id'])


def _delete_network(
    token_id,
    engine_name,
    network_id,
):
    _send_delete(
        token_id,
        OVN_PROVIDER_NETWORKS_URL.format(hostname=engine_name),
        network_id,
    )


def _delete_port(
    token_id,
    engine_name,
    port_id,
):
    _send_delete(
        token_id,
        OVN_PROVIDER_PORTS_URL.format(hostname=engine_name),
        port_id,
    )


def _delete_subnet(
    token_id,
    engine_name,
    subnet_id,
):
    _send_delete(
        token_id,
        OVN_PROVIDER_SUBNETS_URL.format(hostname=engine_name),
        subnet_id,
    )


def _delete_all(prefix):
    engine = prefix.virt_env.engine_vm()
    engine_ip = engine.ip()
    token_id = _get_auth_token(engine_ip)

    networks = _get_networks(token_id, engine_ip)['networks']
    ports = _get_ports(token_id, engine_ip)['ports']
    subnets = _get_subnets(token_id, engine_ip)['subnets']

    for port in ports:
        id = port['id']
        _delete_port(token_id, engine_ip, id)

    for subnet in subnets:
        id = subnet['id']
        _delete_subnet(token_id, engine_ip, id)

    for network in networks:
        id = network['id']
        _delete_network(token_id, engine_ip, id)


def _validate_network(token_id, engine_ip, name, id):
    networks = _get_networks(token_id, engine_ip)['networks']
    for network in networks:
        if network['id'] == id:
            nt.assert_equals(network['id'], id)
            nt.assert_equals(network['name'], NETWORKS[name]['name'])
            return
    raise Exception('Expected network is not present in results')


def _validate_port(token_id, engine_ip, name, id, network_id):
    ports = _get_ports(token_id, engine_ip)['ports']
    for port in ports:
        if port['id'] == id:
            nt.assert_equals(port['id'], id)
            nt.assert_equals(port['network_id'], network_id)
            return
    raise Exception('Expected port is not present in results')


def _validate_subnet(token_id, engine_ip, name, id, network_id):
    subnets = _get_subnets(token_id, engine_ip)['subnets']
    for subnet in subnets:
        if subnet['id'] == id:
            nt.assert_equals(subnet['id'], id)
            nt.assert_equals(subnet['name'], SUBNETS[name]['name'])
            nt.assert_equals(subnet['network_id'], network_id)
            return
    raise Exception('Expected subnet is not present in results')


def _validate_db_empty(token_id, engine_ip):
    networks = _get_networks(token_id, engine_ip)['networks']
    nt.assert_false(networks)
    ports = _get_ports(token_id, engine_ip)['ports']
    nt.assert_false(ports)
    subnets = _get_subnets(token_id, engine_ip)['subnets']
    nt.assert_false(subnets)


@testlib.with_ovirt_prefix
def test_ovn_provider_rest(prefix):
    engine_ip = prefix.virt_env.engine_vm().ip()
    token_id = _get_auth_token(engine_ip)

    _validate_db_empty(token_id, engine_ip)

    network1_id = _add_network(
        token_id,
        engine_ip,
        NETWORK_1,
    )

    subnet1_id = _add_subnet(
        token_id,
        engine_ip,
        SUBNET_1,
        network1_id,
    )

    port1_id = _add_port(
        token_id,
        engine_ip,
        PORT_1,
        network1_id,
    )

    _validate_network(token_id, engine_ip, NETWORK_1, network1_id)
    _validate_port(token_id, engine_ip, PORT_1, port1_id, network1_id)
    _validate_subnet(token_id, engine_ip, SUBNET_1, subnet1_id, network1_id)

    _delete_port(token_id, engine_ip, port1_id)
    _delete_subnet(token_id, engine_ip, subnet1_id)
    _delete_network(token_id, engine_ip, network1_id)

    _validate_db_empty(token_id, engine_ip)


_TEST_LIST = [
    test_ovn_provider_rest,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
