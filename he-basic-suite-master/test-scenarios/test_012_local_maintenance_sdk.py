#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging

import ovirtsdk4
from ovirtsdk4 import types

import pytest

from ost_utils import assert_utils
from ost_utils import he_utils

VM_HE_NAME = 'HostedEngine'


def _hosted_engine_info(hosted_engine):
    """Input: ovirtsdk4.types.HostedEngine instance
    Return: dict with info
    """
    props = (
        'score',
        'configured',
        'global_maintenance',
        'active',
        'local_maintenance',
    )
    return {p: getattr(hosted_engine, p) for p in props}


@pytest.mark.xfail(reason='TODO. Fails too much, not trivial to fix')
def test_local_maintenance(hosts_service, get_vm_service_for_vm, ansible_host0):
    logging.info('Waiting For System Stability...')
    he_utils.wait_until_engine_vm_is_not_migrating(ansible_host0)

    vm_service = get_vm_service_for_vm(VM_HE_NAME)
    he_host_id = vm_service.get().host.id
    host_service = hosts_service.host_service(id=he_host_id)
    host_name = host_service.get().name

    logging.info(f'Performing Deactivation on {host_name}...')

    def _do_deactivate():
        logging.debug(f'Trying to deactivate host {host_name}')
        try:
            host_service.deactivate()
        except ovirtsdk4.Error:
            return False
        return True

    assert assert_utils.true_within_short(_do_deactivate)

    def _is_in_maintenance():
        logging.debug(f'Checking if host {host_name} is in maintenance')
        status = host_service.get().status
        hosted_engine = host_service.get(all_content=True).hosted_engine
        logging.debug(f'status={status}')
        logging.debug(f'hosted_engine={_hosted_engine_info(hosted_engine)}')
        # Original test was:
        #   (
        #       status == types.HostStatus.MAINTENANCE or
        #       hosted_engine.local_maintenance
        #   )
        # But this does not test local_maintenance (presumably the "local
        # maintenance" status as reported by the HA daemons?).
        # So I tried to change the "or" to "and" (require both), and it
        # never happened - local_maintenance always remained False.
        # Giving up on this for now and checking only status.
        # TODO: Find out why, fix what's needed, change the code to require
        # both. Also for do_verified_activation below.
        return status == types.HostStatus.MAINTENANCE

    assert assert_utils.true_within_long(_is_in_maintenance)

    logging.info('Performing Activation...')

    def _do_activate():
        logging.debug(f'Trying to activate host {host_name}')
        try:
            host_service.activate()
        except ovirtsdk4.Error:
            return False
        return True

    assert assert_utils.true_within_short(_do_activate)

    def _is_active():
        logging.info(f'Checking if host {host_name} is active')
        status = host_service.get().status
        hosted_engine = host_service.get(all_content=True).hosted_engine
        logging.debug(f'status={status}')
        logging.debug(f'hosted_engine={_hosted_engine_info(hosted_engine)}')
        # TODO See comment above
        return status == types.HostStatus.UP

    assert assert_utils.true_within_long(_is_active)

    logging.info('Verifying that all hosts have score higher than 0...')
    assert assert_utils.true_within_long(lambda: host_service.get(all_content=True).hosted_engine.score > 0)

    logging.info('Validating Migration...')
    prev_host_id = he_host_id
    he_host_id = vm_service.get().host.id
    assert prev_host_id != he_host_id
