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

import pytest

from ost_utils import ansible
from ost_utils.ansible import facts
from ost_utils.ansible import module_mappers
from ost_utils.ansible import private_dir

from ost_utils.pytest.fixtures.artifacts import artifacts_dir


@pytest.fixture(scope="session")
def ansible_all():
    return module_mappers.all()


@pytest.fixture(scope="session")
def ansible_engine():
    return module_mappers.engine()


@pytest.fixture(scope="session")
def ansible_storage():
    return module_mappers.storage()


@pytest.fixture(scope="session")
def ansible_hosts():
    return module_mappers.hosts()


@pytest.fixture(scope="session")
def ansible_host0():
    return module_mappers.host0()


@pytest.fixture(scope="session")
def ansible_host1():
    return module_mappers.host1()


@pytest.fixture(scope="session")
def ansible_by_hostname():
    return module_mappers.module_mapper_for


@pytest.fixture(scope="session")
def ansible_engine_facts():
    return facts.engine()


@pytest.fixture(scope="session")
def ansible_storage_facts():
    return facts.storage()


@pytest.fixture(scope="session")
def ansible_host0_facts():
    return facts.host0()


@pytest.fixture(scope="session")
def ansible_host1_facts():
    return facts.host1()


@pytest.fixture(scope="session", autouse=True)
def ansible_clean_private_dirs():
    yield
    private_dir.PrivateDir.cleanup()


@pytest.fixture(scope="session", autouse=True)
def ansible_collect_logs(artifacts_dir, ansible_clean_private_dirs):
    yield
    ansible.LogsCollector.save(artifacts_dir)
