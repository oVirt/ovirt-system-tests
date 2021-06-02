# -*- coding: utf-8 -*-
#
# Copyright 2021 Red Hat, Inc.
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

from ost_utils import backend as _backend


@pytest.fixture(scope="session")
def backend():
    return _backend.default_backend()


@pytest.fixture(scope="session")
def deploy_scripts(backend):
    return backend.deploy_scripts()


@pytest.fixture(scope="session")
def all_hostnames(backend):
    return backend.hostnames()


@pytest.fixture(scope="session")
def hosts_hostnames(backend):
    return backend.hosts_hostnames()


@pytest.fixture(scope="session")
def storage_hostname(backend):
    return backend.storage_hostname()


@pytest.fixture(scope="session")
def ansible_inventory(backend):
    return backend.ansible_inventory()
