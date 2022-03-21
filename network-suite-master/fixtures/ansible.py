#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

import pytest

from testlib import address_family

from ost_utils import ansible
from ost_utils.ansible import private_dir


@pytest.fixture(scope="session")
def af(tested_ip_version):
    return address_family.AF(tested_ip_version)


@pytest.fixture(scope="session")
def engine_facts(ansible_engine_facts, af):
    return _machine_facts(ansible_engine_facts.get_all(), af)


@pytest.fixture(scope="session")
def host0_facts(ansible_host0_facts, af):
    return _machine_facts(ansible_host0_facts.get_all(), af)


@pytest.fixture(scope="session")
def host1_facts(ansible_host1_facts, af):
    return _machine_facts(ansible_host1_facts.get_all(), af)


@pytest.fixture(scope="session")
def storage_facts(ansible_storage_facts, af):
    return _machine_facts(ansible_storage_facts.get_all(), af)


@pytest.fixture(scope="session", autouse=True)
def ansible_clean_private_dirs():
    try:
        yield
    finally:
        private_dir.PrivateDir.cleanup()


@pytest.fixture(scope="session", autouse=True)
def ansible_collect_logs(artifacts_dir, ansible_clean_private_dirs):
    try:
        yield
    finally:
        ansible.LogsCollector.save(artifacts_dir)


def _machine_facts(facts_dict, af):
    if af.is6:
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
    def fqdn(self):
        return self._facts['ansible_fqdn']

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
            ipv6['address'] for ipv6 in self._facts[f'ansible_{iface_name}']['ipv6'] if ipv6['scope'] == 'global'
        )
