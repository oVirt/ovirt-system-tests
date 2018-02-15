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

from lib.ansiblelib import Playbook

OS_AUTH_URL = 'https://{}:35357/v2.0'
OS_USERNAME = 'admin@internal'
PLAYBOOK_DIR = os.path.join(os.environ.get('SUITE'), 'ansible')


class HostConfigurationFailure(Exception):
    pass


@pytest.fixture(scope='module')
def os_client_config(engine):
    cloud_config = {
        'clouds': {
            'ovirt': {
                'auth': {
                    'auth_url': OS_AUTH_URL.format(engine.ip()),
                    'username': OS_USERNAME,
                    'password': engine.metadata['ovirt-engine-password']
                },
                'verify': False
            }
        }
    }
    os_client_config_file_path = os.path.join(PLAYBOOK_DIR, 'clouds.yml')
    with open(os_client_config_file_path, 'w') as cloud_config_file:
        yaml.dump(cloud_config, cloud_config_file, default_flow_style=False)

    original_os_client_config_file = os.environ.get('OS_CLIENT_CONFIG_FILE')
    os.environ['OS_CLIENT_CONFIG_FILE'] = os_client_config_file_path
    yield
    if original_os_client_config_file:
        os.environ['OS_CLIENT_CONFIG_FILE'] = original_os_client_config_file
    else:
        del os.environ['OS_CLIENT_CONFIG_FILE']


def test_ovn_provider_create_scenario(os_client_config):
    _test_ovn_provider('create_scenario.yml')


def test_ovn_provider_cleanup_scenario(os_client_config):
    _test_ovn_provider('cleanup_scenario.yml')


def _test_ovn_provider(playbook_name):
    playbook_path = os.path.join(PLAYBOOK_DIR, playbook_name)
    playbook = Playbook([playbook_path])
    playbook.run()

    assert not playbook.execution_stats.failures
    assert not playbook.idempotency_check_stats.failures
    assert playbook.execution_stats.changed.get('localhost', 0) > 0
    assert not playbook.idempotency_check_stats.changed
