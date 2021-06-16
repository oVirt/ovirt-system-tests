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

import ipaddress
import pytest

from ost_utils import ansible
from ost_utils.ansible import private_dir


@pytest.fixture(scope="session")
def engine_facts(ansible_engine_facts):
    return MachineFacts(ansible_engine_facts.get_all())


@pytest.fixture(scope="session")
def host0_facts(ansible_host0_facts):
    return MachineFacts(ansible_host0_facts.get_all())


@pytest.fixture(scope="session")
def host1_facts(ansible_host1_facts):
    return MachineFacts(ansible_host1_facts.get_all())


@pytest.fixture(scope="session", autouse=True)
def ansible_clean_private_dirs():
    yield
    private_dir.PrivateDir.cleanup()


@pytest.fixture(scope="session", autouse=True)
def ansible_collect_logs(artifacts_dir, ansible_clean_private_dirs):
    yield
    ansible.LogsCollector.save(artifacts_dir)


class MachineFacts(object):

    def __init__(self, ansible_facts_dict, ssh_password='123456'):
        self._facts = ansible_facts_dict
        self._ssh_password = ssh_password

    @property
    def default_ip(self):
        return self._facts['ansible_default_ipv4']['address']

    @property
    def url_ip(self):
        return self._make_url_ip()

    @property
    def hostname(self):
        return self._facts['ansible_hostname']

    @property
    def ssh_password(self):
        return self._ssh_password

    def _make_url_ip(self):
        ip = ipaddress.ip_address(self.default_ip)
        return self.default_ip if ip.version == 4 else f'[{self.default_ip}]'
