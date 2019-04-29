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
import ansible_runner


class AnsibleExecutionFailure(Exception):
    pass


class Playbook(object):
    def __init__(self, playbook, extra_vars={}):
        self._execution_stats = None
        self._idempotency_check_stats = None
        self._playbook = playbook
        self._extra_vars = extra_vars

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
            inventory='localhost ansible_connection=local')
        if runner.status != 'successful':
            raise AnsibleExecutionFailure
        return Playbook._stats(runner)

    @staticmethod
    def _stats(runner):
            last_event = list(
                filter(
                    lambda x:
                    'event' in x and x['event'] == 'playbook_on_stats',
                    runner.events
                )
            )
            if not last_event:
                return None
            last_event = last_event[0]['event_data']
            return dict(skipped=last_event['skipped'],
                        ok=last_event['ok'],
                        dark=last_event['dark'],
                        failures=last_event['failures'],
                        processed=last_event['processed'],
                        changed=last_event['changed'])
