# -*- coding: utf-8 -*-
#
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

import os

import pytest

from ost_utils import ansible
from ost_utils.pytest.fixtures.artifacts import artifacts_dir


ANSIBLE_ENGINE_PATTERN = "~lago-.*-engine"
ANSIBLE_HOSTS_PATTERN = "~lago-.*-host-[0-9]"
ANSIBLE_HOST0_PATTERN = "~lago-.*-host-0"
ANSIBLE_HOST1_PATTERN = "~lago-.*-host-1"


@pytest.fixture(scope="session")
def ansible_engine():
    return ansible.module_mapper_for(ANSIBLE_ENGINE_PATTERN)


@pytest.fixture(scope="session")
def ansible_hosts():
    return ansible.module_mapper_for(ANSIBLE_HOSTS_PATTERN)


@pytest.fixture(scope="session")
def ansible_host0():
    return ansible.module_mapper_for(ANSIBLE_HOST0_PATTERN)


@pytest.fixture(scope="session")
def ansible_host1():
    return ansible.module_mapper_for(ANSIBLE_HOST1_PATTERN)


@pytest.fixture(scope="session")
def ansible_by_hostname(ansible_engine, ansible_host0, ansible_host1):

    # ugly, but local and gets the job done for now
    def by_hostname(hostname):
        if "engine" in hostname:
            return ansible_engine
        if "host-0" in hostname:
            return ansible_host0
        if "host-1" in hostname:
            return ansible_host1

    return by_hostname


@pytest.fixture(scope="session")
def ansible_engine_facts():
    return ansible._AnsibleFacts(ANSIBLE_ENGINE_PATTERN)


@pytest.fixture(scope="session")
def ansible_host0_facts():
    return ansible._AnsibleFacts(ANSIBLE_HOST0_PATTERN)


@pytest.fixture(scope="session")
def ansible_host1_facts():
    return ansible._AnsibleFacts(ANSIBLE_HOST1_PATTERN)


@pytest.fixture(scope="session", autouse=True)
def ansible_clean_private_dirs():
    yield
    ansible._AnsiblePrivateDir.cleanup()


@pytest.fixture(scope="session", autouse=True)
def ansible_collect_logs(artifacts_dir, ansible_clean_private_dirs):
    yield
    ansible._AnsibleLogs.save(artifacts_dir)
