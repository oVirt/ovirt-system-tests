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
import shutil
import tempfile
import threading

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
    config_builder = _AnsibleConfigBuilder()
    config_builder.host_pattern = host_pattern
    return _AnsibleModuleMapper(config_builder)


def _run_ansible(config_builder):
    runner = ansible_runner.Runner(config=config_builder.prepare())
    runner.run()

    if runner.status != 'successful':
        raise AnsibleExecutionError(
            rc=runner.rc,
            stdout=runner.stdout.read()
        )

    return runner


# We need one ansible private directory per thread because:
#  - when multiple threads try to access the same directory
#    ansible-runner reports a conflict
#  - when using a new private directory for each ansible
#    module call, we cannot refer to gathered and cached facts
class _AnsiblePrivateDir(object):

    thread_local = threading.local()
    all_dirs = set()

    @classmethod
    def get(cls):
        dir = cls.thread_local.__dict__.setdefault('dir', tempfile.mkdtemp())
        cls.all_dirs.add(dir)
        return dir

    @classmethod
    def cleanup(cls):
        for dir in cls.all_dirs:
            shutil.rmtree(dir)


class _AnsibleConfigBuilder(object):

    def __init__(self):
        self.inventory = os.environ["ANSIBLE_INVENTORY_FILE"]
        self.extravars = {"ansible_user": "root"}
        self.host_pattern = None
        self.module = None
        self.module_args = None

    def prepare(self):
        config = ansible_runner.RunnerConfig(
            inventory=self.inventory,
            extravars=self.extravars,
            host_pattern=self.host_pattern,
            module=self.module,
            module_args=self.module_args,
            private_data_dir=_AnsiblePrivateDir.get()
        )
        config.prepare()
        return config


class _AnsibleModuleArgsMapper(object):

    def __init__(self, config_builder):
        self.config_builder = config_builder

    def __call__(self, *args, **kwargs):
        self.config_builder.module_args = " ".join((
            " ".join(args),
            " ".join("{}={}".format(k, v) for k, v in kwargs.items())
        )).strip()
        return _run_ansible(self.config_builder)


class _AnsibleModuleMapper(object):

    def __init__(self, config_builder):
        self.config_builder = config_builder

    def __getattr__(self, name):
        self.config_builder.module = name
        return _AnsibleModuleArgsMapper(self.config_builder)


# Similar to '_AnsiblePrivateDir', we need the 'facts_gathered'
# boolean to have a per-thread value. See the rationale above.
class _AnsibleFacts(object):

    def __init__(self, host_pattern):
        self._thread_local = threading.local()
        self._module_mapper = module_mapper_for(host_pattern)

    @property
    def facts_gathered(self):
        return self._thread_local.__dict__.setdefault('facts_gathered', False)

    @facts_gathered.setter
    def facts_gathered(self, value):
        self._thread_local.facts_gathered = value

    def get(self, fact):
        if not self.facts_gathered:
            self.refresh()
        runner = self._module_mapper.debug(var=fact)
        events = sorted(
            (e for e in runner.events if 'created' in e),
            key=lambda e: e['created']
        )

        for event in reversed(events):
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
        self._module_mapper.gather_facts()
        self.facts_gathered = True
