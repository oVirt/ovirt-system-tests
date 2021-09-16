#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from __future__ import absolute_import

import os

from ost_utils.ansible.collection import engine_setup


def test_initialize_engine(
    working_dir,
    ansible_engine,
    ansible_inventory,
    engine_ip,
    root_dir,
    ssh_key_file,
    engine_hostname,
    engine_answer_file_path,
    artifacts_dir,
    ansible_execution_environment,
):
    if os.environ.get('ENABLE_DEBUG_LOGGING'):
        ansible_engine.shell(
            'sed -i '
            '-e "/.*logger category=\\"org.ovirt\\"/{ n; s/INFO/DEBUG/ }" '
            '-e "/.*logger category=\\"org.ovirt.engine.core.bll\\"/{ n; s/INFO/DEBUG/ }" '  # noqa: E501
            '-e "/.*<root-logger>/{ n; s/INFO/DEBUG/ }" '
            '/usr/share/ovirt-engine/services/ovirt-engine/ovirt-engine.xml.in'
        )

    engine_setup(
        working_dir,
        ansible_engine,
        ansible_inventory,
        engine_ip,
        ssh_key_path=ssh_key_file,
        artifacts_dir=artifacts_dir,
        execution_environment_tag=ansible_execution_environment,
        engine_hostname=engine_hostname,
        answer_file_path=engine_answer_file_path,
        ovirt_engine_setup_offline='true',
        ovirt_engine_setup_engine_configs=[
            {'key': 'VdsLocalDisksLowFreeSpace', 'value': '400'},
            {'key': 'OvfUpdateIntervalInMinutes', 'value': '10'},
            {'key': 'ServerRebootTimeout', 'value': '120'},
            {'key': 'ClientModeVncDefault', 'value': 'NoVnc'},
        ],
    )
    ansible_engine.shell('ss -anp')

    ansible_engine.systemd(name='ovirt-engine-notifier', state='started')
    ansible_engine.systemd(name='ovirt-engine', state='started')
    ansible_engine.systemd(name='ovirt-engine-dwhd', state='started')
