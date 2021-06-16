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
from ost_utils.ansible import private_dir

from testlib import suite


@pytest.fixture(scope="session")
def engine_facts(ansible_engine_facts):
    return _machine_facts(ansible_engine_facts.get_all())


@pytest.fixture(scope="session")
def host0_facts(ansible_host0_facts):
    return _machine_facts(ansible_host0_facts.get_all())


@pytest.fixture(scope="session")
def host1_facts(ansible_host1_facts):
    return _machine_facts(ansible_host1_facts.get_all())


@pytest.fixture(scope="session", autouse=True)
def ansible_clean_private_dirs():
    yield
    private_dir.PrivateDir.cleanup()


@pytest.fixture(scope="session", autouse=True)
def ansible_collect_logs(artifacts_dir, ansible_clean_private_dirs):
    yield
    ansible.LogsCollector.save(artifacts_dir)


def _machine_facts(facts_dict):
    if suite.af().is6:
        return MachineFacts6(facts_dict)
    else:
        return MachineFacts4(facts_dict)


class MachineFacts(object):

    def __init__(self, ansible_facts_dict, ssh_password='123456'):
        self._facts = ansible_facts_dict
        self._ssh_password = ssh_password

    @property
    def hostname(self):
        return self._facts['ansible_hostname']

    @property
    def ssh_password(self):
        return self._ssh_password

    def default_ip(self, urlize=False):
        return self._urlized_ip(self._get_ip_for_iface('eth0'), urlize)

    def storage_ip(self, urlize=False):
        return self._urlized_ip(self._get_ip_for_iface('eth1'), urlize)

    def _urlized_ip(self, ip, urlize):
        return ip

    def _get_ip_for_iface(self, iface_name):
        return NotImplementedError()


class MachineFacts4(MachineFacts):

    def __init__(self, ansible_facts_dict, ssh_password='123456'):
        super(MachineFacts4, self).__init__(ansible_facts_dict, ssh_password)

    def _get_ip_for_iface(self, iface_name):
        return self._facts[f'ansible_{iface_name}']['ipv4']['address']


class MachineFacts6(MachineFacts):

    def __init__(self, ansible_facts_dict, ssh_password='123456'):
        super(MachineFacts6, self).__init__(ansible_facts_dict, ssh_password)

    def _urlized_ip(self, ip, urlize=False):
        return f'[{ip}]' if urlize else ip

    def _get_ip_for_iface(self, iface_name):
        return next(
            ipv6['address'] for ipv6
            in self._facts[f'ansible_{iface_name}']['ipv6']
            if ipv6['scope'] == 'global'
        )
