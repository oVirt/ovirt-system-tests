#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging

import pytest

from ost_utils import he_utils
from ost_utils import assertions
from ost_utils import constants
from ost_utils.ansible import AnsibleExecutionError


def test_set_global_maintenance(ansible_host0):
    logging.info('Waiting For System Stability...')
    he_utils.wait_until_engine_vm_is_not_migrating(ansible_host0)

    he_utils.set_and_test_global_maintenance_mode(ansible_host0, True)

    assertions.assert_true_within_short(
        lambda: he_utils.all_hosts_state_global_maintenance(ansible_host0)
    )
    logging.info('Global maintenance state set on all hosts')


def test_restart_he_vm(ansible_by_hostname, ansible_host0):
    host_name = he_utils.host_name_running_he_vm(ansible_host0)
    ansible_host = ansible_by_hostname(host_name)

    logging.info(f'Engine VM is on host {host_name}, restarting the VM')
    _shutdown_he_vm(ansible_host)
    _restart_services(ansible_host)
    _start_he_vm(ansible_host)
    _wait_for_engine_health(ansible_host)


def test_clear_global_maintenance(ansible_host0):
    logging.info('Waiting For System Stability...')
    he_utils.wait_until_engine_vm_is_not_migrating(ansible_host0)

    he_utils.set_and_test_global_maintenance_mode(ansible_host0, False)

    assertions.assert_true_within_long(
        lambda: he_utils.no_hosts_state_global_maintenance(ansible_host0)
    )
    logging.info('Global maintenance state cleared on all hosts')


def _shutdown_he_vm(ansible_host):
    ansible_host.shell('hosted-engine --vm-shutdown')
    logging.info('Waiting for the engine VM to be down...')
    assertions.assert_true_within_short(
        lambda: he_utils.engine_vm_is_down(ansible_host)
    )


def _restart_services(ansible_host):
    logging.info('Stopping services...')
    ansible_host.shell(
        'systemctl stop vdsmd supervdsmd ovirt-ha-broker ovirt-ha-agent'
    )

    logging.info('Starting services...')
    ansible_host.shell(
        'systemctl start vdsmd supervdsmd ovirt-ha-broker ovirt-ha-agent'
    )

    logging.info('Waiting for agent to be ready...')
    assertions.assert_true_within_long(
        lambda: _ha_agent_is_ready(ansible_host)
    )
    logging.info('Agent is ready.')


def _ha_agent_is_ready(ansible_host):
    try:
        ansible_host.shell('hosted-engine --vm-status')
        return True
    except AnsibleExecutionError:
        return False


def _start_he_vm(ansible_host):
    logging.info('Starting the engine VM...')
    ansible_host.shell('hosted-engine --vm-start')
    logging.info('Waiting for the engine VM to be UP...')
    assertions.assert_true_within_short(
        lambda: he_utils.engine_vm_is_up(ansible_host)
    )
    logging.info('Engine VM is UP.')


def _wait_for_engine_health(ansible_host):
    logging.info('Waiting for the engine to start...')
    assertions.assert_true_within(
        lambda: any(
            host_data['engine-status']['health'] == 'good'
            for host_data in he_utils.he_status(ansible_host)['hosts'].values()
        ),
        constants.ENGINE_VM_RESTART_TIMEOUT,
    )
    logging.info('Engine is running.')
