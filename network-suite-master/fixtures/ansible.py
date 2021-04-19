# Copyright 2020-2021 Red Hat, Inc.
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

import pytest

from ost_utils import ansible
from ost_utils.ansible import facts
from ost_utils.ansible import private_dir


@pytest.fixture(scope="session")
def engine_facts():
    return AnsibleFactsCache(facts.engine())


@pytest.fixture(scope="session")
def host0_facts():
    return AnsibleFactsCache(facts.host0())


@pytest.fixture(scope="session")
def host1_facts():
    return AnsibleFactsCache(facts.host1())


@pytest.fixture(scope="session", autouse=True)
def ansible_clean_private_dirs():
    yield
    private_dir.PrivateDir.cleanup()


@pytest.fixture(scope="session", autouse=True)
def ansible_collect_logs(artifacts_dir, ansible_clean_private_dirs):
    yield
    ansible.LogsCollector.save(artifacts_dir)


class AnsibleFactsCache(object):

    """
    ost_utils.ansible.ansible_facts retrieves information from
    the remote machine whenever its get(attribute) is called.
    AnsibleFactsCache caches the remote responses while also serving as
    an adapter that encapsulates the ost_utils.
    ansible library from the network suite.
    """

    def __init__(self, ansible_facts):
        self._ipv4_default = ansible_facts.get('ansible_default_ipv4')
        self._hostname = ansible_facts.get('ansible_hostname')

    @property
    def ipv4_default_address(self):
        return self._ipv4_default.get('address')

    @property
    def hostname(self):
        return self._hostname

    @property
    def ssh_password(self):
        return '123456'
