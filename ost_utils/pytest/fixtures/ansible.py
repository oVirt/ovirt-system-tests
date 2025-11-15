#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

import pytest

from ost_utils import ansible
from ost_utils.ansible import inventory
from ost_utils.ansible import module_mappers
from ost_utils.ansible import private_dir
from ost_utils.ansible.facts import Facts

from ost_utils.pytest.fixtures.artifacts import artifacts_dir


@pytest.fixture(scope="session")
def ansible_all(ansible_by_hostname):
    return ansible_by_hostname("*")


@pytest.fixture(scope="session")
def ansible_engine(ansible_by_hostname, backend_engine_hostname):
    return ansible_by_hostname(backend_engine_hostname)


@pytest.fixture(scope="session")
def ansible_dwh(ansible_by_hostname, backend_dwh_hostname):
    return ansible_by_hostname(backend_dwh_hostname)


@pytest.fixture(scope="session")
def ansible_storage(ansible_by_hostname, storage_hostname):
    return ansible_by_hostname(storage_hostname)


@pytest.fixture(scope="session")
def ansible_hosts(ansible_by_hostname, hosts_hostnames):
    return ansible_by_hostname(hosts_hostnames)


@pytest.fixture(scope="session")
def ansible_host0(ansible_by_hostname, host0_hostname):
    return ansible_by_hostname(host0_hostname)


@pytest.fixture(scope="session")
def ansible_host1(ansible_by_hostname, host1_hostname):
    return ansible_by_hostname(host1_hostname)


@pytest.fixture(scope="session")
def ansible_by_hostname(ansible_inventory):
    def module_mapper_for(host_pattern):
        inventory = ansible_inventory.dir
        return module_mappers.ModuleMapper(inventory, host_pattern)

    def seq_to_ansible_pattern(seq):
        # https://docs.ansible.com/ansible/latest/user_guide/intro_patterns.html#using-regexes-in-patterns
        return f"~({'|'.join(seq)})"

    def short_name(name):
        # lago inventory uses short domain names, not FQDN.
        # In HE suites, host-0 is deployed with its FQDN, and this
        # is what the engine returns to us when asking which host
        # runs some VM. So when we feed this answer from the engine
        # to current function, strip the domain part.
        # TODO: Perhaps fix lago to include both short and full names?
        # Alternatively, fix all relevant code to always use only
        # full names, never short ones.
        return name.split('.')[0]

    def get_ansible_by_hostname(names):
        # names should be either a string (and then we use it directly)
        # or a tuple/list (and then we concatenate to create a pattern)
        host_pattern = (
            short_name(names) if isinstance(names, str) else seq_to_ansible_pattern(short_name(name) for name in names)
        )
        return module_mapper_for(host_pattern)

    return get_ansible_by_hostname


@pytest.fixture(scope="session")
def ansible_engine_facts(ansible_engine):
    return Facts(ansible_engine)


@pytest.fixture(scope="session")
def ansible_dwh_facts(ansible_dwh):
    return Facts(ansible_dwh)


@pytest.fixture(scope="session")
def ansible_storage_facts(ansible_storage):
    return Facts(ansible_storage)


@pytest.fixture(scope="session")
def ansible_host0_facts(ansible_host0):
    return Facts(ansible_host0)


@pytest.fixture(scope="session")
def ansible_host1_facts(ansible_host1):
    return Facts(ansible_host1)


@pytest.fixture(scope="session", autouse=True)
def ansible_clean_private_dirs():
    yield
    private_dir.PrivateDir.cleanup()


@pytest.fixture(scope="session", autouse=True)
def ansible_collect_logs(artifacts_dir, ansible_clean_private_dirs):
    yield
    ansible.LogsCollector.save(artifacts_dir)


@pytest.fixture(scope="session")
def ansible_inventory(backend, working_dir):
    inv = inventory.Inventory(working_dir)
    inv.add('backend', backend.ansible_inventory_str())
    return inv
