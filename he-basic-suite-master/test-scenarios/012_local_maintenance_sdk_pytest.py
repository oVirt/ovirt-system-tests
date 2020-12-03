#
# Copyright 2014-2020 Red Hat, Inc.
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
import time

import ovirtsdk4
from ovirtsdk4 import types

import pytest

from test_utils import ipv6_utils

from ost_utils import assertions

VM_HE_NAME = 'HostedEngine'
WAIT_VALUE = 300


@pytest.fixture(scope='module', autouse=True)
def setup_module():
    ipv6_utils.open_connection_to_api_with_ipv6_on_relevant_suite()


def test_local_maintenance(hosts_service, get_vm_service_for_vm):
    logging.info('Waiting For System Stability...')
    # TODO: Replace arbitrary sleep with something more sensible
    time.sleep(WAIT_VALUE)

    vm_service = get_vm_service_for_vm(VM_HE_NAME)
    he_host_id = vm_service.get().host.id
    host_service = hosts_service.host_service(id=he_host_id)

    logging.info('Performing Deactivation...')
    host_service.deactivate()
    assertions.assert_true_within_long(
        lambda: (
            host_service.get().status == types.HostStatus.MAINTENANCE or
            host_service.get(all_content=True).hosted_engine.local_maintenance
        ),
        allowed_exceptions=[ovirtsdk4.Error],
    )

    logging.info('Performing Activation...')
    host_service.activate()
    assertions.assert_true_within_long(
        lambda: host_service.get().status == types.HostStatus.UNASSIGNED
    )

    logging.info('Waiting For System Stability...')
    # TODO: Replace arbitrary sleep with something more sensible
    time.sleep(WAIT_VALUE)

    logging.info('Waiting For Maintenance...')
    assertions.assert_true_within_long(
        lambda: not host_service.get(all_content=True).hosted_engine.local_maintenance
    )

    logging.info('Waiting For Score...')
    assertions.assert_true_within_long(
        lambda: host_service.get(all_content=True).hosted_engine.score > 0
    )

    logging.info('Validating Migration...')
    prev_host_id = he_host_id
    he_host_id = vm_service.get().host.id
    assert prev_host_id != he_host_id
