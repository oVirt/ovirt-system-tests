# Copyright 2017-2020 Red Hat, Inc.
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

from ovirtlib import hostlib
from ovirtlib.sdkentity import EntityNotFoundError

ROOT_PASSWORD = '123456'


@pytest.fixture(scope='session')
def host_0(system, default_cluster, ansible_host0_facts):
    return _create_host(system, default_cluster, ansible_host0_facts)


@pytest.fixture(scope='session')
def host_0_up(host_0):
    _wait_for_host_install(host_0)
    return host_0


@pytest.fixture(scope='session')
def host_1(system, default_cluster, ansible_host1_facts):
    return _create_host(system, default_cluster, ansible_host1_facts)


@pytest.fixture(scope='session')
def host_1_up(host_1):
    _wait_for_host_install(host_1)
    return host_1


@pytest.fixture(scope='session')
def host_in_ovs_cluster(
        system, ovs_cluster, default_cluster, default_data_center):
    host_id = default_cluster.host_ids()[0]
    host = hostlib.Host(system)
    host.import_by_id(host_id)
    host.wait_for_up_status(timeout=hostlib.HOST_TIMEOUT_LONG)
    with host.toggle_cluster(ovs_cluster):
        host.sync_all_networks()
        default_data_center.wait_for_up_status()
        yield host
    host.sync_all_networks()
    default_data_center.wait_for_up_status()


def _wait_for_host_install(host):
    host.wait_for_up_status(timeout=hostlib.HOST_TIMEOUT_LONG)


@pytest.fixture(scope='session', autouse=True)
def install_hosts_to_save_time(host_0, host_1):
    """add hosts before any test starts so they can install in parallel"""
    pass


def _create_host(system, default_cluster, ansible_host_facts):
    host = hostlib.Host(system)
    try:
        host.import_by_name(ansible_host_facts.get("ansible_hostname"))
    except EntityNotFoundError:
        host.create(
            default_cluster, ansible_host_facts.get("ansible_hostname"),
            ansible_host_facts.get("ansible_default_ipv4").get("address"),
            ROOT_PASSWORD)
    return host
