#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import os
import pytest
import openstack
import yaml

from ovirtlib.providerlib import OpenStackNetwork
from ovirtlib.providerlib import OpenStackNetworkProvider
from testlib import suite


OPENSTACK_AUTH_URL = 'https://{}:35357/v2.0'
OPENSTACK_CLIENT_CONFIG_FILE = 'clouds.yml'
DEFAULT_CLOUD = 'ovirt'
DEFAULT_OVN_PROVIDER_NAME = 'ovirt-provider-ovn'
DEFAULT_OVN_NETWORK_NAME = 'default_network_name'
DEFAULT_OVN_SUBNET_CIDR = '10.0.0.0/24'
DEFAULT_OVN_SUBNET_NAME = 'default_subnet_name'
DEFAULT_OVN_SUBNET_GW = '10.0.0.3'


@pytest.fixture(scope='session')
def openstack_client_config(engine_facts, engine_full_username, engine_password, ovirt_provider_ovn_with_ip_fqdn):
    cloud_config = {
        'clouds': {
            DEFAULT_CLOUD: {
                'auth': {
                    'auth_url': OPENSTACK_AUTH_URL.format(engine_facts.default_ip(urlize=True)),
                    'username': engine_full_username,
                    'password': engine_password,
                },
                'verify': False,
            }
        }
    }
    os_client_config_file_path = os.path.join(suite.suite_dir(), OPENSTACK_CLIENT_CONFIG_FILE)
    with open(os_client_config_file_path, 'w', encoding='utf-8') as cloud_config_file:
        yaml.dump(cloud_config, cloud_config_file, default_flow_style=False)

    original_os_client_config_file = os.environ.get('OS_CLIENT_CONFIG_FILE')
    os.environ['OS_CLIENT_CONFIG_FILE'] = os_client_config_file_path
    yield DEFAULT_CLOUD
    if original_os_client_config_file is not None:
        os.environ['OS_CLIENT_CONFIG_FILE'] = original_os_client_config_file
    else:
        del os.environ['OS_CLIENT_CONFIG_FILE']


@pytest.fixture(scope='session')
def default_ovn_provider_client(openstack_client_config):
    """
    Returns a openstack connection configured to connect
    to the default ovn provider.
    """
    return openstack.connect(cloud=openstack_client_config)


@pytest.fixture(scope='session')
def default_ovn_provider(system):
    openstack_network_provider = OpenStackNetworkProvider(system)
    openstack_network_provider.import_by_name(DEFAULT_OVN_PROVIDER_NAME)
    with openstack_network_provider.disable_auto_sync():
        yield openstack_network_provider


@pytest.fixture(scope='session')
def ovn_network(default_ovn_provider, default_ovn_provider_client):
    network_name = DEFAULT_OVN_NETWORK_NAME
    network = default_ovn_provider_client.create_network(network_name)
    try:
        subnet = default_ovn_provider_client.create_subnet(
            network.id,
            cidr=DEFAULT_OVN_SUBNET_CIDR,
            subnet_name=DEFAULT_OVN_SUBNET_NAME,
            enable_dhcp=True,
            gateway_ip=DEFAULT_OVN_SUBNET_GW,
        )
        yield network
        default_ovn_provider_client.delete_subnet(subnet.id)
    finally:
        default_ovn_provider_client.delete_network(network.id)


@pytest.fixture(scope='session')
def ovirt_external_network(default_ovn_provider, default_data_center, ovn_network):
    openstack_network = OpenStackNetwork(default_ovn_provider)
    openstack_network.import_by_id(str(ovn_network.id))
    ovirt_network = openstack_network.create_external_network(default_data_center)
    try:
        yield ovirt_network
    finally:
        ovirt_network.remove()
