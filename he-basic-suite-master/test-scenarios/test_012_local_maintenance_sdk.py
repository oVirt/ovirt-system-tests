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


def test_local_maintenance(
    hosts_service, get_vm_service_for_vm, ansible_host0
):
    logging.info('Waiting For System Stability...')
    he_utils.wait_until_engine_vm_is_not_migrating(ansible_host0)

    vm_service = get_vm_service_for_vm(VM_HE_NAME)
    he_host_id = vm_service.get().host.id
    host_service = hosts_service.host_service(id=he_host_id)

    def do_verified_deactivation():
        logging.debug(f'Trying to deactivate host {host_service.get().name}')
        try:
            host_service.deactivate()
        except ovirtsdk4.Error:
            # Ignore. Just return the result and let the caller fail if needed
            pass
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

    logging.info('Performing Deactivation...')
    assert assert_utils.true_within_long(do_verified_deactivation)

    def do_verified_activation():
        logging.info(f'Trying to activate host {host_service.get().name}')
        try:
            host_service.activate()
        except ovirtsdk4.Error:
            # Ignore. Just return the result and let the caller fail if needed
            pass
        status = host_service.get().status
        hosted_engine = host_service.get(all_content=True).hosted_engine
        logging.debug(f'status={status}')
        logging.debug(f'hosted_engine={_hosted_engine_info(hosted_engine)}')
        # TODO See comment above
        return status == types.HostStatus.UP

    logging.info('Performing Activation...')
    assert assert_utils.true_within_long(do_verified_activation)

    logging.info('Verifying that all hosts have score higher than 0...')
    assert assert_utils.true_within_long(
        lambda: host_service.get(all_content=True).hosted_engine.score > 0
    )

    logging.info('Validating Migration...')
    prev_host_id = he_host_id
    he_host_id = vm_service.get().host.id
    assert prev_host_id != he_host_id
