#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import logging
import ansible_runner

LOGGER = logging.getLogger(__name__)


class AnsibleExecutionFailure(Exception):
    pass


class Playbook:
    def __init__(self, playbook, private_dir, extra_vars=None):
        self._execution_stats = None
        self._idempotency_check_stats = None
        self._playbook = playbook
        self._extra_vars = extra_vars if extra_vars else {}
        self._extra_vars['ansible_python_interpreter'] = 'python3'
        self._private_dir = private_dir

    @property
    def execution_stats(self):
        return self._execution_stats

    @property
    def idempotency_check_stats(self):
        return self._idempotency_check_stats

    def run(self):
        self._execution_stats = self._run_playbook_executor()
        self._idempotency_check_stats = self._run_playbook_executor()

    def _run_playbook_executor(self):
        runner = ansible_runner.run(
            playbook=self._playbook,
            extravars=self._extra_vars,
            inventory='localhost ansible_connection=local',
            private_data_dir=self._private_dir,
        )
        if runner.status != 'successful':
            LOGGER.error(
                f'failed running playbook {self._playbook} '
                f'with status {runner.status}.\n'
                f'stdout: {runner.stdout.read()}'
            )
            raise AnsibleExecutionFailure
        return runner.stats
