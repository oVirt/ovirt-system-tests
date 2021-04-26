#
# Copyright 2020-2021 Red Hat, Inc.
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

import ansible_runner

from ost_utils import backend
from ost_utils.ansible import config_builder as cb
from ost_utils.ansible import patterns

import logging
LOGGER = logging.getLogger(__name__)


class AnsibleExecutionError(Exception):

    def __init__(self, rc, stdout):
        self.rc = rc
        self.stdout = stdout

    def __str__(self):
        return f"Error running ansible: rc={self.rc}, stdout={self.stdout}"


def all():
    return module_mapper_for(patterns.all())


def engine():
    return module_mapper_for(patterns.engine())


def host0():
    return module_mapper_for(patterns.host0())


def host1():
    return module_mapper_for(patterns.host1())


def hosts():
    return module_mapper_for(patterns.hosts())


def storage():
    return module_mapper_for(patterns.storage())


def module_mapper_for(host_pattern):
    inventory = backend.default_backend().ansible_inventory()
    # lago inventory uses short domain names, not FQDN.
    # In HE suites, host-0 is deployed with its FQDN, and this
    # is what the engine returns to us when asking which host
    # runs some VM. So when we feed this answer from the engine
    # to current function, strip the domain part.
    # TODO: Perhaps fix lago to include both short and full names?
    # Alternatively, fix all relevant code to always use only
    # full names, never short ones.
    return ModuleMapper(inventory, host_pattern.split('.')[0])


def _run_ansible_runner(config_builder):
    runner = ansible_runner.Runner(config=config_builder.prepare())
    LOGGER.debug(f'_run_ansible_runner: before run: {runner}')
    runner.run()
    LOGGER.debug(f'_run_ansible_runner: after run: {runner}')

    if runner.status != 'successful':
        raise AnsibleExecutionError(
            rc=runner.rc,
            stdout=runner.stdout.read()
        )

    return _find_result(runner.events)


def _find_result(ansible_events):
    """Finds the result object for the ansible module call"""

    events = sorted(
        (e for e in ansible_events if 'created' in e),
        key=lambda e: e['created']
    )

    for event in reversed(events):
        event_data = event.get('event_data', None)
        if event_data is not None:
            res = event_data.get('res', None)
            if res is not None:
                return res

    return None


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
        self.config_builder.module_args = " ".join((
            " ".join(args),
            " ".join("{}={}".format(k, v) for k, v in kwargs.items())
        )).strip()
        LOGGER.debug('ModuleArgsMapper: __call__: '
                     f'module_args={self.config_builder.module_args}')
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
        return (
            'ModuleMapper<'
            f'inventory={self.inventory} '
            f'host_pattern={self.host_pattern}'
            '>'
        )
