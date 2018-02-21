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
import os
import pytest
import yaml

from lib.providerlib import OpenStackImageProviders


OPENSTACK_AUTH_URL = 'https://{}:35357/v2.0'
OPENSTACK_USERNAME = 'admin@internal'
OVIRT_IMAGE_REPO_NAME = 'ovirt-image-repository'
OVIRT_IMAGE_REPO_URL = 'http://glance.ovirt.org:9292/'
OPENSTACK_CLIENT_CONFIG_FILE = 'clouds.yml'


@pytest.fixture(scope='session')
def ovirt_image_repo(system):
    openstack_image_providers = OpenStackImageProviders(system)
    if openstack_image_providers.is_provider_available(OVIRT_IMAGE_REPO_NAME):
        openstack_image_providers.import_by_name(OVIRT_IMAGE_REPO_NAME)
    else:
        openstack_image_providers.create(name=OVIRT_IMAGE_REPO_NAME,
                                         url=OVIRT_IMAGE_REPO_URL)
        openstack_image_providers.wait_until_available()


@pytest.fixture(scope='session')
def openstack_client_config(engine):
    cloud_config = {
        'clouds': {
            'ovirt': {
                'auth': {
                    'auth_url': OPENSTACK_AUTH_URL.format(engine.ip()),
                    'username': OPENSTACK_USERNAME,
                    'password': engine.metadata['ovirt-engine-password']
                },
                'verify': False
            }
        }
    }
    os_client_config_file_path = os.path.join(
        os.environ.get('SUITE'), OPENSTACK_CLIENT_CONFIG_FILE
    )
    with open(os_client_config_file_path, 'w') as cloud_config_file:
        yaml.dump(cloud_config, cloud_config_file, default_flow_style=False)

    original_os_client_config_file = os.environ.get('OS_CLIENT_CONFIG_FILE')
    os.environ['OS_CLIENT_CONFIG_FILE'] = os_client_config_file_path
    yield
    if original_os_client_config_file is not None:
        os.environ['OS_CLIENT_CONFIG_FILE'] = original_os_client_config_file
    else:
        del os.environ['OS_CLIENT_CONFIG_FILE']
