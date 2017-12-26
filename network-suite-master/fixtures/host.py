# Copyright 2017 Red Hat, Inc.
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
import time

import pytest

from lib import hostlib


HOST_0_DOMAIN = 'lago-network-suite-master-host-0'
HOST_1_DOMAIN = 'lago-network-suite-master-host-1'


@pytest.fixture(scope='session')
def host_0(env, system, default_cluster):
    vm = env.get_vms()[HOST_0_DOMAIN]
    host = hostlib.Host(system)
    host.create(default_cluster.name, vm)
    with host.wait_for_up_status():
        # TODO: There's currently a NPE (bz#1514853) in Engine's
        # scheduling logic (CPU usage). Once it is resolved, remove this
        time.sleep(30)

    return host


@pytest.fixture(scope='session')
def host_1(env, system, default_cluster):
    vm = env.get_vms()[HOST_1_DOMAIN]
    host = hostlib.Host(system)
    host.create(default_cluster.name, vm)
    with host.wait_for_up_status():
        # TODO: There's currently a NPE (bz#1514853) in Engine's
        # scheduling logic (CPU usage). Once it is resolved, remove this
        time.sleep(30)

    return host
