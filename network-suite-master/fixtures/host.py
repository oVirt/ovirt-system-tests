# Copyright 2017-2018 Red Hat, Inc.
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
import time

import pytest

from lib import hostlib

from fixtures.engine import SUITE


HOST_0_DOMAIN = '-'.join(['lago', re.sub('\.', '-', SUITE), 'host', '0'])
HOST_1_DOMAIN = '-'.join(['lago', re.sub('\.', '-', SUITE), 'host', '1'])


@pytest.fixture(scope='session')
def host_0(env, system, default_cluster):
    vm = env.get_vms()[HOST_0_DOMAIN]
    host = hostlib.Host(system)
    host.create(
        default_cluster, vm.name(), vm.ip(), str(vm.root_password()))
    return host


@pytest.fixture(scope='session')
def host_0_up(host_0):
    _wait_for_host_install(host_0)
    return host_0


@pytest.fixture(scope='session')
def host_1(env, system, default_cluster):
    vm = env.get_vms()[HOST_1_DOMAIN]
    host = hostlib.Host(system)
    host.create(
        default_cluster, vm.name(), vm.ip(), str(vm.root_password()))
    return host


@pytest.fixture(scope='session')
def host_1_up(host_1):
    _wait_for_host_install(host_1)
    return host_1


def _wait_for_host_install(host):
    host.wait_for_up_status(timeout=15 * 60)
    # TODO: There's currently a NPE (bz#1514853) in Engine's
    # scheduling logic (CPU usage). Once it is resolved, remove this
    time.sleep(20)


@pytest.fixture(scope='session', autouse=True)
def install_hosts_to_save_time(host_0, host_1):
    """add hosts before any test starts so they can install in parallel"""
    pass
