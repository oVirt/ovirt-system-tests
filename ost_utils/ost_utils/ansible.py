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

import errno
import glob
import itertools
import json
import os
import shutil
import tempfile
import threading
import yaml

import ansible_runner
from ost_utils import shell

SUITE_PATH = os.environ.get('SUITE')
_ENGINE = 'engine'
_HOST0 = 'host-0'
_HOST1 = 'host-1'
_LAGO_ENGINE_PATTERN = '~lago-.*-' + _ENGINE
_LAGO_HOST0_PATTERN = '~lago-.*-' + _HOST0
_LAGO_HOST1_PATTERN = '~lago-.*-' + _HOST1

from ost_utils import backend


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

    return _find_result(runner.events)


def _find_result(ansible_events):
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
        if 'dir' not in cls.thread_local.__dict__:
            path = tempfile.mkdtemp()
            cls.thread_local.__dict__['dir'] = path
            cls.all_dirs.add(path)
        return cls.thread_local.__dict__['dir']

    @classmethod
    def event_data_files(cls):
        return itertools.chain.from_iterable(
            glob.iglob(os.path.join(dir, "artifacts/*/job_events/*.json"))
            for dir in cls.all_dirs
        )

    @classmethod
    def cleanup(cls):
        for dir in cls.all_dirs:
            shutil.rmtree(dir)
        cls.all_dirs.clear()


class _AnsibleConfigBuilder(object):

    def __init__(self):
        self.inventory = backend.default_backend().ansible_inventory()
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
            private_data_dir=_AnsiblePrivateDir.get(),
            quiet=True
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
        result = self._module_mapper.debug(var=fact)

        if result is not None:
            value = result.get(fact, None)
            if value == "VARIABLE IS NOT DEFINED!":
                raise AnsibleFactNotFound(fact)
            if value is not None:
                return value

        raise AnsibleFactNotFound(fact)

    def refresh(self):
        self._module_mapper.gather_facts()
        self.facts_gathered = True


class _AnsibleLogs(object):

    @classmethod
    def save(cls, target_dir):
        logs_path = os.path.join(target_dir, "ansible_logs")
        raw_logs_path = os.path.join(logs_path, "raw")

        try:
            os.makedirs(raw_logs_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        cls._save_raw_events(
            _AnsiblePrivateDir.event_data_files(), raw_logs_path
        )

        cls._save_events_stdouts(
            _AnsiblePrivateDir.event_data_files(), logs_path
        )

    @classmethod
    def _save_raw_events(cls, event_data_files, target_dir):
        for event_file in event_data_files:
            shutil.copy(event_file, target_dir)

    @classmethod
    def _save_events_stdouts(cls, event_data_files, target_dir):
        all_events = cls._load_events(event_data_files)

        for host, events in all_events.items():
            log_path = os.path.join(target_dir, host)
            with open(log_path, 'w') as log_file:
                for event in sorted(events, key=lambda e: e['created']):
                    log_file.write(event['stdout'])
                    log_file.write('\n')

    @classmethod
    def _load_events(cls, event_data_files):
        events = {}

        for path in event_data_files:
            with open(path) as event_file:
                event = json.load(event_file)
                if cls._should_include_event(event):
                    host = event['event_data']['host']
                    events.setdefault(host, []).append(event)

        return events

    @classmethod
    def _should_include_event(cls, event):
        # no stdout - nothing to log
        if len(event.get('stdout', '')) == 0:
            return False

        # if we can't sort an event by its creation time
        # we can't log it in an understandable way
        if event.get('created', None) is None:
            return False

        # logs are grouped by host, so we need this information
        if event.get('event_data', {}).get('host', None) is None:
            return False

        return True


class ArtifactsCollector(object):

    def __init__(self, host_pattern, host_key, artifacts_target_dir):
        self._module_mapper = module_mapper_for(host_pattern)
        self.host_key = host_key
        self.artifacts_target_dir = artifacts_target_dir
        self.domain_name = None

    def _retrieve_artifacts_list(self):
        """
        :return: [] list of files to collect on this machine
        """
        with open(os.path.join(SUITE_PATH, 'LagoInitFile'), "r") as file:
            yaml_dict = yaml.safe_load(file)
            domains_dict = yaml_dict['domains']

            self.domain_name = ''.join(
                [key for key in domains_dict.keys() if self.host_key in key]
            )
        return domains_dict[self.domain_name]['artifacts']

    def collect(self):
        artifacts_list_string = ','.join(self._retrieve_artifacts_list())
        archive_name = "artifacts.tar.gz"
        local_archive_dir = os.path.join(
            self.artifacts_target_dir, "test_logs", self.domain_name)
        local_archive_path = os.path.join(local_archive_dir, archive_name)
        remote_archive_path = os.path.join("/tmp", archive_name)
        os.makedirs(local_archive_dir, exist_ok=True)

        self._module_mapper.archive(
            path=artifacts_list_string, dest=remote_archive_path
        )
        self._module_mapper.fetch(
            src=remote_archive_path, dest=local_archive_path, flat='yes'
        )
        shell.shell(
            ["tar", "-xf", local_archive_path, "-C", local_archive_dir]
        )
        shell.shell(["rm", local_archive_path])


class EngineArtifactsCollector(ArtifactsCollector):
    def __init__(self, artifacts_dir):
        super(EngineArtifactsCollector, self).__init__(
            _LAGO_ENGINE_PATTERN, _ENGINE, artifacts_dir)


class Host0ArtifactsCollector(ArtifactsCollector):
    def __init__(self, artifacts_dir):
        super(Host0ArtifactsCollector, self).__init__(
            _LAGO_HOST0_PATTERN, _HOST0, artifacts_dir)


class Host1ArtifactsCollector(ArtifactsCollector):
    def __init__(self, artifacts_dir):
        super(Host1ArtifactsCollector, self).__init__(
            _LAGO_HOST1_PATTERN, _HOST1, artifacts_dir)
