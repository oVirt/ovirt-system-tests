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

import logging
import random

import ovirtsdk4 as sdk
import ovirtsdk4.types as types

from ost_utils import general_utils


LOGGER = logging.getLogger(__name__)


def random_up_host(hosts_service, dc_name):
    """
    Returns random host in 'UP' state from datacenter. When using this
    function the expectation is that the datacenter and the hosts went
    through a complete setup process including handling of host flapping.
    """

    host = find_single_up_host(hosts_service, dc_name)

    if host is None:
        raise RuntimeError('No up hosts found!')

    return host


def random_up_host_service(hosts_service, dc_name):
    host = random_up_host(hosts_service, dc_name)
    return hosts_service.host_service(id=host.id)


def find_single_up_host(hosts_service, dc_name):
    """
    Returns random host in 'UP' state from datacenter. This does not handle
    host flapping! See 'wait_for_flapping_host' below.
    """

    up_hosts = _up_hosts(hosts_service, dc_name)

    if len(up_hosts) > 0:
        random_host = random.choice(up_hosts)
        LOGGER.debug(f'Using {random_host.id} up host')
        return random_host

    if not _poke_nonop_hosts(hosts_service, dc_name):
        _detect_problematic_hosts(hosts_service, dc_name)

    return None


def all_hosts_up(hosts_service, dc_name):
    """
    Returns true if all hosts in datacenter are in 'UP' state. This does
    not handle host flapping! See 'wait_for_flapping_host' below.
    """

    up_hosts = _up_hosts(hosts_service, dc_name)
    all_hosts = _all_hosts(hosts_service, dc_name)

    if len(up_hosts) == len(all_hosts):
        return True

    if not _poke_nonop_hosts(hosts_service, dc_name):
        _detect_problematic_hosts(hosts_service, dc_name)

    return False


def wait_for_flapping_host(hosts_service, dc_name, host_id=None):
    """
    There's a bug in oVirt that causes a freshly added host to reach
    'UP' status, switch to other status for a moment and then 'UP' back
    again. To handle this so called 'host flapping' we track the status
    of the hosts and wait some time for it to settle.
    """

    query = f'datacenter={dc_name} AND status={types.HostStatus.UP.value}'

    if host_id is not None:
        query += f' AND id={host_id}'

    hosts_up_seen = 0

    for _ in general_utils.linear_retrier(attempts=12, iteration_sleeptime=10):
        up_host_count = len(hosts_service.list(search=query))
        LOGGER.debug(f'Query: "{query}" found {up_host_count} hosts up')

        if up_host_count >= hosts_up_seen:
            if hosts_up_seen:
                return
            hosts_up_seen = up_host_count
        else:
            if hosts_up_seen > 0:
                LOGGER.warning('Host flapping detected!')
            hosts_up_seen = 0

    raise RuntimeError('Host flapping detection failed!')


def _all_hosts(hosts_service, dc_name):
    return hosts_service.list(search=f'datacenter={dc_name}')


def _up_hosts(hosts_service, dc_name):
    return [
        host
        for host in _all_hosts(hosts_service, dc_name)
        if host.status == types.HostStatus.UP
    ]


def _poke_nonop_hosts(hosts_service, dc_name):
    # sometimes a host is fast enough to go up without master SD,
    # it then goes NonOperational with 5min autorecovery, let's poke it
    poked = False
    nonop_hosts = [
        host
        for host in _all_hosts(hosts_service, dc_name)
        if host.status == types.HostStatus.NON_OPERATIONAL
    ]

    for host in nonop_hosts:
        host_service = hosts_service.host_service(host.id)
        try:
            host_service.activate()
            poked = True
        except sdk.Error as e:
            if 'Related operation is currently in progress' not in str(e):
                raise

    return poked


def _detect_problematic_hosts(hosts_service, dc_name):
    expected_statuses = {
        types.HostStatus.INSTALLING,
        types.HostStatus.INITIALIZING,
        types.HostStatus.REBOOT,
        types.HostStatus.NON_RESPONSIVE,
        types.HostStatus.UP,
    }
    statuses = {h.name: h.status for h in _all_hosts(hosts_service, dc_name)}
    LOGGER.debug(f'_detect_problematic_hosts: {statuses}')
    problematic_hosts = {
        hname: status
        for hname, status in statuses.items()
        if status not in expected_statuses
    }
    if len(problematic_hosts):
        raise RuntimeError(
            f'Some hosts failed installation: {problematic_hosts}'
        )
