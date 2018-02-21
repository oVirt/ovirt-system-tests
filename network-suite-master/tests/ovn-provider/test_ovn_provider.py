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


from lib.ansiblelib import Playbook
from testlib import suite


PLAYBOOK_DIR = os.path.join(os.environ.get('SUITE'), 'ansible')


pytestmark = suite.SKIP_SUITE_42


class HostConfigurationFailure(Exception):
    pass


def test_ovn_provider_create_scenario(openstack_client_config):
    _test_ovn_provider('create_scenario.yml')


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
