#
# Copyright 2018 Red Hat, Inc.
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
from collections import namedtuple
from contextlib import contextmanager

from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager

PbexOptions = namedtuple('PbexOptions',
                         ['listtags', 'listtasks', 'listhosts', 'syntax',
                          'connection', 'module_path', 'forks', 'remote_user',
                          'private_key_file', 'ssh_common_args',
                          'ssh_extra_args', 'sftp_extra_args',
                          'scp_extra_args', 'become', 'become_method',
                          'become_user', 'verbosity', 'check', 'diff'])
_PBEX_OPTIONS = PbexOptions(listtags=False,
                            listtasks=False,
                            listhosts=False,
                            syntax=False,
                            connection='local',
                            module_path=None,
                            forks=100,
                            remote_user=None,
                            private_key_file=None,
                            ssh_common_args=None,
                            ssh_extra_args=None,
                            sftp_extra_args=None,
                            scp_extra_args=None,
                            become=False,
                            become_method=None,
                            become_user=None,
                            verbosity=0,
                            check=False,
                            diff=False)


class AnsibleExecutionFailure(Exception):
    pass


class StatsHandlerError(Exception):
    pass


class StatsHandlers(object):
    funcs = set()

    @staticmethod
    def execute(stats):
        """Is called if new stats are available"""
        for func in StatsHandlers.funcs:
            func(stats)

    @staticmethod
    def register(func):
        """Registers function func to be called if new stats are available

        :param func: function that accepts one argument
        """
        StatsHandlers.funcs.add(func)

    @staticmethod
    def unregister(func):
        StatsHandlers.funcs.remove(func)


@contextmanager
def register_stats_handler(func):
    StatsHandlers.register(func)
    try:
        yield
    finally:
        StatsHandlers.unregister(func)


class Playbook(object):
    def __init__(self, playbooks, extra_vars={}):
        self._execution_stats = None
        self._idempotency_check_stats = None
        self._pbex_args = Playbook._create_pbex_args(playbooks, extra_vars)

    @staticmethod
    def _create_pbex_args(playbooks, extra_vars):
        loader = DataLoader()
        inventory = InventoryManager(loader=loader)
        variable_manager = VariableManager(loader=loader, inventory=inventory)
        variable_manager.extra_vars = extra_vars
        return {
            'playbooks': playbooks,
            'inventory': inventory,
            'variable_manager': variable_manager,
            'loader': loader,
            'options': _PBEX_OPTIONS,
            'passwords': {},
        }

    @property
    def execution_stats(self):
        return self._execution_stats

    @property
    def idempotency_check_stats(self):
        return self._idempotency_check_stats

    def run(self):
        stats = []
        with register_stats_handler(lambda new_stats: stats.append(new_stats)):
            self._run_playbook_executor()
            # repeated call to ensure idempotency
            self._run_playbook_executor()

        if len(stats) != 2:
            raise StatsHandlerError

        self._execution_stats = stats[0]
        self._idempotency_check_stats = stats[1]

    def _run_playbook_executor(self):
        pbex = PlaybookExecutor(**self._pbex_args)
        if pbex.run() != 0:
            raise AnsibleExecutionFailure
