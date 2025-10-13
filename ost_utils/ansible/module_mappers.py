#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging

import ansible_runner

from ost_utils.ansible import config_builder as cb
from ost_utils.debuginfo_utils import obj_info

LOGGER = logging.getLogger(__name__)


class AnsibleExecutionError(Exception):
    def __init__(self, rc, stdout):
        self.rc = rc
        self.stdout = stdout

    def __str__(self):
        return f"Error running ansible: rc={self.rc}, stdout={self.stdout}"


def _run_ansible_runner(config_builder):
    runner = ansible_runner.Runner(config=config_builder.prepare())
    LOGGER.debug(f'_run_ansible_runner: before run: {runner}')
    runner.run()
    LOGGER.debug(f'_run_ansible_runner: after run: {obj_info(runner)}')

    # Always collect results, so that we log them
    results = _find_result(runner.events)

    if runner.status != 'successful':
        raise AnsibleExecutionError(rc=runner.rc, stdout=runner.stdout.read())

    return results


def _find_result(ansible_events):
    """Finds the result object for the ansible module call"""

    events = sorted(
        (e for e in ansible_events if 'created' in e),
        key=lambda e: e['created'],
    )

    results = {}

    for event in reversed(events):
        LOGGER.debug(f'_find_result: {obj_info(event)}')
        event_data = event.get('event_data', None)
        if event_data is not None:
            res = event_data.get('res', None)
            if res is not None:
                results[event_data['host']] = res
            elif len(results) > 0:
                break

    if len(results) == 0:
        LOGGER.error('No result from ansible-runner')
        LOGGER.error('Event UUIDs: %s', [e.get('uuid') for e in events])
        raise RuntimeError('No result from ansible-runner')
    elif len(results) == 1:
        return results[next(iter(results))]

    return results


class ModuleArgsMapper:
    """Passes ansible module arguments to ansible_runner's config.

    This class works along with ModuleMapper. While ModuleMapper
    maps the names of the functions you try to call on its instances
    to ansible module names, this class does the same with the functions'
    arguments, i.e. for:

        mm = ModuleMapper(inventory, host_pattern)
        mm.shell(some, arguments)

    the ModuleMapper will map the call to use an ansible module called 'shell'
    and ModuleArgsMapper will pass 'some' and 'arguments' as the arguments
    for the module.

    """

    def __init__(self, inventory, host_pattern, module):
        self.config_builder = cb.ConfigBuilder()
        self.config_builder.inventory = inventory
        self.config_builder.host_pattern = host_pattern
        self.config_builder.module = module

    def __call__(self, *args, **kwargs):
        self.config_builder.module_args = " ".join(
            (
                " ".join(args),
                " ".join(f"{k}={v}" for k, v in kwargs.items()),
            )
        ).strip()
        LOGGER.debug('ModuleArgsMapper: __call__: ' f'module_args={self.config_builder.module_args}')
        return _run_ansible_runner(self.config_builder)

    def __str__(self):
        return f'ModuleArgsMapper<config_builder={self.config_builder}>'


class ModuleMapper:
    """Passes ansible module name to ansible_runner's config.

    When you call an arbitrary function on an instance of this class,
    the name of the function will be used as the name of the ansible module
    you're trying to use, i.e. for:

        mm = ModuleMapper(inventory, host_pattern)
        mm.shell(some, arguments)

    the underlying logic will pass 'shell' as the name of the ansible
    module to use.

    """

    def __init__(self, inventory, host_pattern):
        self.inventory = inventory
        self.host_pattern = host_pattern

    def __getattr__(self, name):
        res = ModuleArgsMapper(self.inventory, self.host_pattern, module=name)
        LOGGER.debug(f'ModuleMapper __getattr__: {res}')
        return res

    def __str__(self):
        return 'ModuleMapper<' f'inventory={self.inventory} ' f'host_pattern={self.host_pattern}' '>'
