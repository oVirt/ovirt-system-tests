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
import urlparse
from contextlib import contextmanager

import ovirtsdk4
import requests

import nose.tools as nt

from ovirtlago import testlib
from ovirtsdk4 import types

import test_utils
from test_utils import network_utils_v4
from test_utils import versioning


VM0_NAME = 'vm0'
CLUSTER_NAME = 'test-cluster'
IFACE_NAME = 'eth2'

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
        'cidr': '1.1.1.0/24',
        'ip_version': 4
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


def _get_datacenter_id(api):
    return api.system_service().data_centers_service().list()[0].id


@contextmanager
def _disable_auto_sync(api, provider_id):
    provider_service = (
        api.system_service()
           .openstack_network_providers_service()
           .provider_service(provider_id)
    )
    original_auto_sync = provider_service.get().auto_sync
    provider_service.update(
        types.OpenStackNetworkProvider(
            auto_sync=False
        )
    )
    try:
        yield
    finally:
        if original_auto_sync:
            provider_service.update(
                types.OpenStackNetworkProvider(
                    auto_sync=original_auto_sync
                )
            )


def _import_network_to_ovirt(api, provider_id, network_id, datacenter_id):
    network_service = (
        api.system_service()
           .openstack_network_providers_service()
           .provider_service(provider_id)
           .networks_service()
           .network_service(network_id)
    )
    network_service.import_(
        async=False,
        data_center=ovirtsdk4.types.DataCenter(
            id=datacenter_id
        ),
    )


def _get_ovirt_network(api, datacenter_id, network_name):
    networks_service = (
        api.system_service()
           .data_centers_service()
           .data_center_service(datacenter_id)
           .networks_service()
    )
    networks = networks_service.list()
    for network in networks:
        if network.name == NETWORKS[network_name]['name']:
            return network.id
    raise Exception(
        'External network %s not found' % NETWORKS[network_name]['name']
    )


def _remove_network_from_ovirt(api, datacenter_id, network_id):
    network_service = (
        api.system_service()
           .data_centers_service()
           .data_center_service(datacenter_id)
           .networks_service()
           .network_service(network_id)
    )
    network_service.remove()


def _add_network_to_cluster(api, datacenter_id, ovirt_network_id):
    cluster_service = test_utils.get_cluster_service(
        api.system_service(), CLUSTER_NAME)

    nt.assert_true(
        cluster_service.networks_service().add(
            network=types.Network(
                id=ovirt_network_id,
                required=False
            ),
        )
    )


def _hotplug_network_to_vm(api, vm_name, network_name, iface_name):
    engine = api.system_service()

    profiles_service = engine.vnic_profiles_service()
    profile = next(profile for profile in profiles_service.list() if profile.name == network_name)

    nics_service = test_utils.get_nics_service(engine, vm_name)
    nics_service.add(
        types.Nic(
            name=iface_name,
            vnic_profile=types.VnicProfile(
                id=profile.id,
            ),
        ),
    )


def _remove_iface_from_vm(api, vm_name, iface_name):
    nics_service = test_utils.get_nics_service(api.system_service(), vm_name)
    nic = next(nic for nic in nics_service.list() if nic.name == iface_name)

    nic_service = nics_service.nic_service(nic.id)
    nic_service.deactivate()
    testlib.assert_true_within_short(
        lambda:
        nic_service.get().plugged == False
    )
    nic_service.remove()


@versioning.require_version(4, 2)
@testlib.with_ovirt_api4
@testlib.with_ovirt_prefix
def use_ovn_provider(prefix, api):
    engine = api.system_service()
    engine_ip = prefix.virt_env.engine_vm().ip()
    provider_id = network_utils_v4.get_default_ovn_provider_id(engine)

    token_id = _get_auth_token(engine_ip)

    _validate_db_empty(token_id, engine_ip)

    with _disable_auto_sync(api, provider_id):
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

        datacenter_id = _get_datacenter_id(api)
        _import_network_to_ovirt(api, provider_id, network1_id, datacenter_id)
        ovirt_network_id = _get_ovirt_network(api, datacenter_id, NETWORK_1)
        _add_network_to_cluster(api, datacenter_id, ovirt_network_id)
        _hotplug_network_to_vm(api, VM0_NAME, NETWORK_1, IFACE_NAME)
        _remove_iface_from_vm(api, VM0_NAME, IFACE_NAME)
        _remove_network_from_ovirt(api, datacenter_id, ovirt_network_id)

        _delete_port(token_id, engine_ip, port1_id)
        _delete_subnet(token_id, engine_ip, subnet1_id)
        _delete_network(token_id, engine_ip, network1_id)

    _validate_db_empty(token_id, engine_ip)


_TEST_LIST = [
    use_ovn_provider,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
