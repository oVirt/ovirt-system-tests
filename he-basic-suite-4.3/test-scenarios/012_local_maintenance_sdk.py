#
# Copyright 2014-2019 Red Hat, Inc.
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

from netaddr.ip import IPAddress
import nose.tools as nt
from ovirtlago import testlib
import ovirtsdk4.types as types
import json

import test_utils
from test_utils import network_utils_v4, assert_finished_within_long, ipv6_utils

import logging
import time

VM_HE_NAME = 'HostedEngine'

wait_value = 300


def setup_module():
    ipv6_utils.open_connection_to_api_with_ipv6_on_relevant_suite()


@testlib.with_ovirt_api4
@testlib.with_ovirt_prefix
def local_maintenance(prefix, api):
    logging.info("Waiting For System Stability...")
    time.sleep(wait_value)

    engine = api.system_service()
    vm_service = test_utils.get_vm_service(engine, VM_HE_NAME)
    hosts_service = engine.hosts_service()

    def _current_running_host():
        host_id = vm_service.get().host.id
        host = hosts_service.list(
            search='id={}'.format(host_id))[0]
        return host

    he_host = _current_running_host()

    host_service = hosts_service.host_service(id=he_host.id)

    prev_host_id = he_host.id

    logging.info("Performing Deactivation...")

    host_service.deactivate()

    testlib.assert_true_within_long(
        lambda: host_service.get().status == types.HostStatus.MAINTENANCE or
        host_service.get(all_content=True).hosted_engine.local_maintenance
    )

    logging.info("Performing Activation...")

    host_service.activate()

    testlib.assert_true_within_long(
        lambda: host_service.get().status == types.HostStatus.UNASSIGNED
    )

    logging.info("Waiting For System Stability...")

    time.sleep(wait_value)

    logging.info("Waiting For Maintenance...")

    testlib.assert_true_within_long(
        lambda: not host_service.get(all_content=True).hosted_engine.local_maintenance
    )

    logging.info("Waiting For Score...")

    testlib.assert_true_within_long(
        lambda: host_service.get(all_content=True).hosted_engine.score > 0
    )

    logging.info("Validating Migration...")

    he_host = _current_running_host()

    testlib.assert_true_within_short(
        lambda: prev_host_id != he_host.id
    )


_TEST_LIST = [
    local_maintenance,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
