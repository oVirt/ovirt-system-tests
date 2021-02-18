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

import functools
import pytest

from ost_utils import network_utils


@pytest.fixture(scope="session")
def storage_ips_for_network(ansible_storage_facts):
    return functools.partial(network_utils.get_ips, ansible_storage_facts)


@pytest.fixture(scope="session")
def storage_management_ips(storage_ips_for_network, management_network_name):
    return storage_ips_for_network(management_network_name)


@pytest.fixture(scope="session")
def sd_iscsi_host_ips():
    return 'Please override sd_iscsi_host_ips'


@pytest.fixture(scope="session")
def sd_nfs_host_storage_ip():
    return 'Please override sd_nfs_host_storage_ip'


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host():
    return 'Please override sd_iscsi_ansible_host'
