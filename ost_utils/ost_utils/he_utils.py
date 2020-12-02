#
# Copyright 2020 Red Hat, Inc.
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

import json
import logging

from ost_utils import assertions
from ost_utils.ansible import AnsibleExecutionError


def he_status(ansible_host):
    ret = None

    def get_value():
        nonlocal ret
        ansible_res = ansible_host.shell('hosted-engine --vm-status --json')['stdout']
        try:
            status = json.loads(ansible_res)
        except ValueError:
            raise RuntimeError(f'could not parse JSON: {ansible_res}')
        # This outputs a dict whose keys are either numbers, and then the
        # values are data about the corresponding host, or
        # 'global_maintenance', and then the value is true or false.
        # Put all hosts' data in a new item 'hosts' so that callers do not
        # have to check isdigit themselves.
        # Also: one of the items per host is 'extra', which is a string
        # containing a newline-separated key=value list. Convert this
        # to a dict as well.
        result = {}
        result['global_maintenance'] = status['global_maintenance']
        result['hosts'] = {}
        for i, data in status.items():
            if i.isdigit():
                hostname = data['hostname']
                result['hosts'][hostname] = data
                result['hosts'][hostname]['extra'] = dict(
                    item.split('=')
                    for item in data['extra'].split('\n')
                    if item
                )
        ret = result
        logging.debug(f'he_status: {ret}')
        return ret

    assertions.assert_true_within_short(
        lambda: get_value() is not None,
        allowed_exceptions=[RuntimeError, AnsibleExecutionError]
    )
    return ret


def host_name_running_he_vm(ansible_host):
    """
    Gets an ansible_host (e.g. one of ansible_host0 or ansible_host1).
    The host needs to be part of the cluster already.
    """
    status = he_status(ansible_host)
    for host_data in status['hosts'].values():
        if host_data['engine-status']['vm'] == 'up':
            return host_data['hostname']
    raise RuntimeError('Hosted Engine is not up on any host')


def is_global_maintenance_mode(ansible_host):
    logging.debug('is_global_maintenance_mode: Start')
    return he_status(ansible_host)['global_maintenance']


def set_and_test_global_maintenance_mode(ansible_host, mode):
    """
    Updates the global maintenance mode and tests if the value was stored.

    Sometimes there is a race condition where the command that modifies the global maintenance flag is ignored.
    That is why the maintenance mode is updated repeatedly in a loop until it succeeds.

    'mode' must be a bool value:
    True - set maintenance mode to global
    False - set maintenance mode to none
    """
    def _set_and_test_global_maintenance_mode():
        logging.debug('_set_and_test_global_maintenance_mode: Start')
        ansible_host.shell(
            'hosted-engine '
            '--set-maintenance '
            '--mode={}'.format('global' if mode else 'none')
        )
        logging.debug('_set_and_test_global_maintenance_mode: After setting')
        return is_global_maintenance_mode(ansible_host) == mode

    logging.info(f'set_and_test_global_maintenance_mode: Start, mode={mode}')
    assertions.assert_true_within_short(_set_and_test_global_maintenance_mode)


def _get_hosts_states(ansible_host):
    status = he_status(ansible_host)
    return set(
        host_data['extra']['state']
        for host_data in status['hosts'].values()
    )


def all_hosts_state_global_maintenance(ansible_host):
    return _get_hosts_states(ansible_host) == {'GlobalMaintenance'}


def no_hosts_state_global_maintenance(ansible_host):
    return 'GlobalMaintenance' not in _get_hosts_states(ansible_host)


def engine_vm_is_migrating(ansible_host):
    status = he_status(ansible_host)
    return any(
        'migration' in host_data['engine-status']['detail'].lower()
        for host_data in status['hosts'].values()
    )


def engine_vm_is_up(ansible_host):
    status = he_status(ansible_host)
    return any(
        host_data['engine-status']['vm'].lower() == 'up'
        for host_data in status['hosts'].values()
    )


def engine_vm_is_down(ansible_host):
    status = he_status(ansible_host)
    return all(
        'down' in host_data['engine-status']['vm'].lower()
        for host_data in status['hosts'].values()
    )


def wait_until_engine_vm_is_not_migrating(ansible_host):
    assertions.assert_true_within_long(
        lambda: not engine_vm_is_migrating(ansible_host)
    )
