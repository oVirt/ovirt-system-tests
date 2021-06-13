# Copyright 2017-2021 Red Hat, Inc.
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

from ovirtlib import eventlib
from ovirtlib import hostlib
from ovirtlib import syncutil
from ovirtlib.sdkentity import EntityNotFoundError


ETH0 = 'eth0'
ETH1 = 'eth1'
ETH2 = 'eth2'
ETH3 = 'eth3'


@pytest.fixture(scope='session')
def host_0(system, default_cluster, host0_facts):
    return _create_host(system, default_cluster, host0_facts)


@pytest.fixture(scope='session')
def host_0_up(system, host_0):
    _wait_for_host_install(system, host_0)
    return host_0


@pytest.fixture(scope='session')
def host_1(system, default_cluster, host1_facts):
    return _create_host(system, default_cluster, host1_facts)


@pytest.fixture(scope='session')
def host_1_up(system, host_1):
    _wait_for_host_install(system, host_1)
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


def _wait_for_host_install(system, host):
    host.wait_for_up_status(timeout=hostlib.HOST_TIMEOUT_LONG)
    results = syncutil.re_run(exec_func=host.wait_for_up_status,
                              exec_func_args=(),
                              count=6,
                              interval=10)
    eventlib.EngineEvents(system).add(description=f'OST - retry wait for host '
                                      f'up after install {host.name}: '
                                      f'{[str(r) for r in results]}')
    if isinstance(results[-1], Exception):
        raise results[-1]


@pytest.fixture(scope='session', autouse=True)
def install_hosts_to_save_time(host_0, host_1):
    """add hosts before any test starts so they can install in parallel"""
    pass


def _create_host(system, default_cluster, host_facts):
    host = hostlib.Host(system)
    try:
        host.import_by_name(host_facts.hostname)
        host.root_password = host_facts.ssh_password
    except EntityNotFoundError:
        host.create(default_cluster, host_facts.hostname,
                    host_facts.default_ip, host_facts.ssh_password)
    return host
