# Copyright 2020 Red Hat, Inc.
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


__ANSIBLE_ENGINE_PATTERN = "~lago-.*-engine"
__ANSIBLE_HOST0_PATTERN = "~lago-.*-host-0"
__ANSIBLE_HOST1_PATTERN = "~lago-.*-host-1"


@pytest.fixture(scope="session")
def ansible_engine():
    return ansible.module_mapper_for(__ANSIBLE_ENGINE_PATTERN)


@pytest.fixture(scope="session")
def engine_facts():
    return AnsibleFactsCache(ansible._AnsibleFacts(__ANSIBLE_ENGINE_PATTERN))


@pytest.fixture(scope="session")
def host0_facts():
    return AnsibleFactsCache(ansible._AnsibleFacts(__ANSIBLE_HOST0_PATTERN))


@pytest.fixture(scope="session")
def host1_facts():
    return AnsibleFactsCache(ansible._AnsibleFacts(__ANSIBLE_HOST1_PATTERN))


@pytest.fixture(scope="session", autouse=True)
def _ansible_clean_private_dirs():
    yield
    ansible._AnsiblePrivateDir.cleanup()


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
