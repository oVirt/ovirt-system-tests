# Copyright 2017-2019 Red Hat, Inc.
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
import re

import pytest

from ovirtlib import hostlib
from ovirtlib.sdkentity import EntityNotFoundError

from fixtures.engine import SUITE


HOST_0_DOMAIN = '-'.join(['lago', re.sub('\.', '-', SUITE), 'host', '0'])
HOST_1_DOMAIN = '-'.join(['lago', re.sub('\.', '-', SUITE), 'host', '1'])


@pytest.fixture(scope='session')
def host_0(env, system, default_cluster):
    return _create_host(env, system, default_cluster, HOST_0_DOMAIN)


@pytest.fixture(scope='session')
def host_0_up(host_0):
    _wait_for_host_install(host_0)
    return host_0


@pytest.fixture(scope='session')
def host_1(env, system, default_cluster):
    return _create_host(env, system, default_cluster, HOST_1_DOMAIN)


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
    with hostlib.change_cluster(host, ovs_cluster):
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


def _create_host(env, system, default_cluster, domain_name):
    vm = env.get_vms()[domain_name]
    host = hostlib.Host(system)
    try:
        host.import_by_name(vm.name())
    except EntityNotFoundError:
        host.create(
            default_cluster, vm.name(), vm.ip(), str(vm.root_password()))
    return host
