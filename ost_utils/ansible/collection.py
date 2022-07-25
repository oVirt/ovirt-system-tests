#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import json
import os
import shutil
import socket
import tarfile
import tempfile
import uuid
import yaml


def _run_playbook(ansible_engine, playbook_yaml, ansible_inventory=None, ssh_key_path=None):
    run_uuid = uuid.uuid4()
    tmp_path = tempfile.NamedTemporaryFile().name
    for dir_name in ['inventory', 'env', 'project']:
        ansible_engine.file(path=os.path.join(tmp_path, dir_name), state='directory', recurse='yes')
    if ssh_key_path:
        ansible_engine.copy(
            src=ssh_key_path,
            dest=os.path.join(tmp_path, 'env/ssh_key'),
        )
    if ansible_inventory:
        ansible_engine.copy(
            src=ansible_inventory.dir,
            dest=os.path.join(tmp_path, 'inventory/hosts'),
        )

    ansible_engine.copy(
        content=f"'{yaml.dump(playbook_yaml)}'",
        dest=os.path.join(tmp_path, 'project/playbook.yml'),
    )

    ansible_engine.shell(f'ansible-runner run -i {run_uuid} -vvv -p playbook.yml {tmp_path}')

    return (tmp_path, run_uuid)


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


def infra(ansible_engine, **kwargs):
    playbook_yaml = _get_role_playbook('infra', 'localhost', **kwargs)
    _run_playbook(ansible_engine, playbook_yaml)


def engine_setup(
    ansible_engine,
    ansible_inventory,
    engine_ip,
    engine_hostname,
    answer_file_path,
    ssh_key_path,
    **kwargs,
):

    ansible_engine.copy(
        src=answer_file_path,
        dest='/root/engine-answer-file',
    )

    kwargs['ovirt_engine_setup_answer_file_path'] = '/root/engine-answer-file'

    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)

    config = f'''\
SSO_ALTERNATE_ENGINE_FQDNS="${{SSO_ALTERNATE_ENGINE_FQDNS}} {host_ip} {host_name} {engine_ip}"
'''

    if os.environ.get('ENABLE_DEBUG_LOGGING'):
        config += '''\
ORG_OVIRT_LOG_LEVEL="DEBUG"
KEYCLOAK_LOG_LEVEL="DEBUG"
CORE_BLL_LOG_LEVEL="DEBUG"
ROOT_LOG_LEVEL="DEBUG"
'''

    ansible_engine.copy(
        content=config.replace('\n', '\\n'),
        dest='/etc/ovirt-engine/engine.conf.d/99-ost.conf',
        mode='0644',
    )

    playbook_yaml = _get_role_playbook('engine_setup', engine_hostname, **kwargs)

    _run_playbook(ansible_engine, playbook_yaml, ansible_inventory, ssh_key_path)


def image_template(
    ansible_engine,
    ansible_inventory,
    ssh_key_path,
    engine_hostname,
    **kwargs,
):
    playbook_yaml = _get_role_playbook('image_template', engine_hostname, **kwargs)
    _run_playbook(ansible_engine, playbook_yaml, ansible_inventory, ssh_key_path)


class CollectionMapper:
    def __init__(self, ansible_engine, ansible_host='localhost'):
        self._ansible_engine = ansible_engine
        self.ansible_host = ansible_host

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

        remote_tmp_path, run_uuid = _run_playbook(self._ansible_engine, playbook_yaml)

        return self._collect_module_data(remote_tmp_path, run_uuid)

    def _collect_module_data(self, remote_tmp_path, run_uuid):
        local_tmp_dir = tempfile.mkdtemp()
        archive_name = 'artifacts.tar.gz'
        local_archive_path = os.path.join(local_tmp_dir, archive_name)
        remote_archive_path = os.path.join("/tmp", archive_name)
        job_events_path = os.path.join(local_tmp_dir, str(run_uuid), 'job_events')
        try:
            self._ansible_engine.archive(
                path=os.path.join(remote_tmp_path, 'artifacts', str(run_uuid)),
                dest=remote_archive_path,
            )
            self._ansible_engine.fetch(
                src=remote_archive_path,
                dest=f'{local_tmp_dir}/',
                flat='yes',
            )

            with tarfile.open(local_archive_path, "r:gz") as tar:
                tar.extractall(path=local_tmp_dir)

            job_events = [os.path.join(job_events_path, job_dir) for job_dir in os.listdir(job_events_path)]
            for file in job_events:
                with open(file) as json_file:
                    data = json.load(json_file)
                    if (
                        data.get('event_data', {}).get('task_action', None) == f'ovirt.ovirt.{self.name}'
                        and data.get('event_data').get('res', None) is not None
                    ):
                        return data.get('event_data').get('res')
            return None
        finally:
            shutil.rmtree(local_tmp_dir)
