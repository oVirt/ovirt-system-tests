#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import json
import os
import socket
import yaml

from ost_utils.shell import shell


def _run_playbook(
    playbook_yaml,
    working_dir,
    artifacts_dir,
    execution_environment_tag,
    ansible_inventory=None,
    ssh_key_path=None,
):
    ansible_logs_path = os.path.join(artifacts_dir, 'ansible_logs')

    # Move of the run artifacts to the working_dir because
    # ansible-navigator logs each run artifacts to /tmp/
    ansible_artifacts_tmp_dir = os.path.join(
        ansible_logs_path, 'ansible-artifacts'
    )

    os.makedirs(ansible_artifacts_tmp_dir, exist_ok=True)
    # Create playbook file from passed yaml
    playbook_path = os.path.join(working_dir, 'playbook.yml')
    with open(playbook_path, "w") as file:
        yaml.dump(playbook_yaml, file)

    os.makedirs(ansible_logs_path, exist_ok=True)

    ansible_navigator_log_path = os.path.join(
        ansible_logs_path, 'ansible-navigator.log'
    )

    playbook_log_path = os.path.join(working_dir, 'playbook-artifacts.json')

    # Running the playbook inside a container
    cmd = [
        'ansible-navigator',
        'run',
        playbook_path,
        '-vvv',
        '--execution-environment-image',
        execution_environment_tag,
        '--mode',
        'stdout',
        '--playbook-artifact-save-as',
        playbook_log_path,
        '--ansible-runner-artifact-dir',
        ansible_artifacts_tmp_dir,
        '--execution-environment-volume-mounts',
        f'{ssh_key_path}:{ssh_key_path}',
        '--pull-policy',
        'never',
        '--log-file',
        ansible_navigator_log_path,
        '--log-level',
        'debug',
        '--display-color',
        'false',
    ]

    if ansible_inventory:
        cmd.append('-i')
        cmd.append(ansible_inventory.dir)

    stdout = shell(cmd)

    log_path = os.path.join(ansible_logs_path, 'ansible-collection-stdout.log')
    if stdout:
        with open(log_path, 'a+') as file:
            file.write(stdout + '\n')


def _get_role_playbook(role_name, host, **kwargs):
    playbook = f'''
    - hosts: {host}
      remote_user: root
      roles:
        - {role_name}
      collections:
        - ovirt.ovirt
    '''
    playbook_yaml = yaml.safe_load(playbook)
    playbook_yaml[0]['vars'] = kwargs
    return playbook_yaml


def infra(
    working_dir,
    ansible_inventory,
    artifacts_dir,
    execution_environment_tag,
    **kwargs,
):
    playbook_yaml = _get_role_playbook('infra', 'localhost', **kwargs)
    _run_playbook(
        playbook_yaml,
        working_dir,
        artifacts_dir,
        execution_environment_tag,
    )


def engine_setup(
    working_dir,
    ansible_engine,
    ansible_inventory,
    engine_ip,
    answer_file_path,
    ssh_key_path,
    engine_hostname,
    artifacts_dir,
    execution_environment_tag,
    **kwargs,
):
    kwargs['ovirt_engine_setup_answer_file_path'] = answer_file_path

    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)

    ansible_engine.copy(
        content=f'SSO_ALTERNATE_ENGINE_FQDNS="${{SSO_ALTERNATE_ENGINE_FQDNS}} {host_ip} {host_name} {engine_ip}"\n',  # noqa: E501
        dest='/etc/ovirt-engine/engine.conf.d/99-custom-fqdn.conf',
        mode='0644',
    )

    playbook_yaml = _get_role_playbook(
        'engine_setup', engine_hostname, **kwargs
    )

    _run_playbook(
        playbook_yaml,
        working_dir,
        artifacts_dir,
        execution_environment_tag,
        ansible_inventory,
        ssh_key_path,
    )


def image_template(
    working_dir,
    artifacts_dir,
    execution_environment_tag,
    ansible_inventory,
    ssh_key_path,
    engine_hostname,
    **kwargs,
):
    playbook_yaml = _get_role_playbook(
        'image_template', engine_hostname, **kwargs
    )
    _run_playbook(
        playbook_yaml,
        working_dir,
        artifacts_dir,
        execution_environment_tag,
        ansible_inventory,
        ssh_key_path,
    )


class CollectionMapper:
    def __init__(
        self,
        working_dir,
        artifacts_dir,
        execution_environment_tag,
        ansible_host='localhost',
        ansible_inventory=None,
        ssh_key_path=None,
    ):
        self.working_dir = working_dir
        self.artifacts_dir = artifacts_dir
        self.execution_environment_tag = execution_environment_tag
        self.ansible_host = ansible_host
        self.ansible_inventory = ansible_inventory
        self.ssh_key_path = ssh_key_path

    def __getattr__(self, name):
        self.name = name
        return self

    def __call__(self, **kwargs):
        playbook = f'''
        - hosts: {self.ansible_host}
          tasks:
            - ovirt.ovirt.{self.name}:
        '''
        playbook_yaml = yaml.safe_load(playbook)
        playbook_yaml[0]['tasks'][0][f'ovirt.ovirt.{self.name}'] = kwargs

        _run_playbook(
            playbook_yaml,
            self.working_dir,
            self.artifacts_dir,
            self.execution_environment_tag,
            self.ansible_inventory,
            self.ssh_key_path,
        )

        return self._collect_module_data()

    def _collect_module_data(self):
        playbook_log_path = os.path.join(
            self.working_dir, 'playbook-artifacts.json'
        )
        with open(playbook_log_path) as file:
            data = json.load(file)
            tasks = (data.get('plays')[0]).get('tasks')
            for task in tasks:
                if (
                    task.get('task') == f'ovirt.ovirt.{self.name}'
                    and task.get('res', None) is not None
                ):
                    return task.get('res')
        return None
