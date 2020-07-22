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

from __future__ import absolute_import

"""Convenience functions for ansible runner.

This module provides a couple of helpers that make running ansible modules
with ansible runner more pleasant. An example of direct usage of ansible
runner:

    import ansible_runner
    r = ansible_runner.run(
        private_data_dir='/tmp/demo',
        host_pattern='localhost',
        module='shell',
        module_args='whoami'
    )

    if r.status == 'failed':
        pass  # handle failure

Can be written with the utils below as:

    localhost = module_mapper_for('localhost')
    localhost.shell(cmd='whoami')

which will raise 'AnsibleExecutionError' on failure.

"""

import os
import tempfile

import ansible_runner


class AnsibleExecutionError(Exception):

    def __init__(self, rc, stdout):
        self.rc = rc
        self.stdout = stdout

    def __str__(self):
        return "Error running ansible: rc={}, stdout={}".format(self.rc,
                                                                self.stdout)

class AnsibleFactNotFound(Exception):

    def __init__(self, fact):
        self.fact = fact

    def __str__(self):
        return "Could not find fact: {}".format(self.fact)


def module_mapper_for(host_pattern):
    config = _base_ansible_config()
    config.host_pattern = host_pattern
    return _AnsibleModuleMapper(config)


def _base_ansible_config():
    return ansible_runner.RunnerConfig(
        private_data_dir=tempfile.mkdtemp(),
        inventory=os.environ["ANSIBLE_INVENTORY_FILE"],
        extravars={
            "ansible_user": "root"
        },
    )


def _run_ansible(config):
    config.prepare()
    runner = ansible_runner.Runner(config=config)
    runner.run()

    if runner.status != 'successful':
        raise AnsibleExecutionError(
            rc=runner.rc,
            stdout=runner.stdout.read()
        )

    return runner


class _AnsibleModuleArgsMapper(object):

    def __init__(self, config):
        self.config = config

    def __call__(self, *args, **kwargs):
        self.config.module_args = " ".join((
            " ".join(args),
            " ".join("{}={}".format(k, v) for k, v in kwargs.items())
        )).strip()
        return _run_ansible(self.config)


class _AnsibleModuleMapper(object):

    def __init__(self, config):
        self.config = config

    def __getattr__(self, name):
        self.config.module = name
        return _AnsibleModuleArgsMapper(self.config)


class _AnsibleFacts(object):

    def __init__(self, host_pattern):
        self._facts_gathered = False
        self.module_mapper = module_mapper_for(host_pattern)

    def get(self, fact):
        if not self._facts_gathered:
            self.refresh()
        runner = self.module_mapper.debug(var=fact)
        for event in reversed(tuple(runner.events)):
            event_data = event.get('event_data', None)
            if event_data is not None:
                res = event_data.get('res', None)
                if res is not None:
                    value = res.get(fact, None)
                    if value == "VARIABLE IS NOT DEFINED!":
                        raise AnsibleFactNotFound(fact)
                    if value is not None:
                        return value
        raise AnsibleFactNotFound(fact)

    def refresh(self):
        self.module_mapper.gather_facts()
        self._facts_gathered = True
