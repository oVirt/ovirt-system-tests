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


ANSIBLE_HOST0_PATTERN = "~lago-.*-host-0"
ANSIBLE_HOST1_PATTERN = "~lago-.*-host-1"


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
