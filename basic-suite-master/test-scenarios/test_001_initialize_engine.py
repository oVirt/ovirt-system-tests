#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from __future__ import absolute_import

import os
import os.path

import pytest

from ost_utils.ansible.collection import engine_setup


@pytest.fixture(scope="function")
def xml_with_debug_enabled(ansible_engine):
    xml_path = '/usr/share/ovirt-engine/services/ovirt-engine/ovirt-engine.xml.in'
    xml_tmp_path = f'/tmp/{os.path.basename(xml_path)}'
    if os.environ.get('ENABLE_DEBUG_LOGGING'):
        ansible_engine.shell(f'mv {xml_path} {xml_tmp_path} && cp {xml_tmp_path} {xml_path}')
        ansible_engine.shell(
            'sed -i '
            '-e "/.*logger category=\\"org.ovirt\\"/{ n; s/INFO/DEBUG/ }" '
            '-e "/.*logger category=\\"org.ovirt.engine.core.bll\\"/{ n; s/INFO/DEBUG/ }" '  # noqa: E501
            '-e "/.*logger category=\\"org.keycloak\\"/{ n; s/INFO/DEBUG/ }" '
            '-e "/.*<root-logger>/{ n; s/INFO/DEBUG/ }" '
            f'{xml_path}'
        )
    yield
    if os.environ.get('ENABLE_DEBUG_LOGGING'):
        ansible_engine.shell(f'mv {xml_tmp_path} {xml_path}')


def test_initialize_engine(
    ansible_engine,
    ansible_inventory,
    engine_ip,
    engine_hostname,
    ssh_key_file,
    engine_answer_file_path,
    xml_with_debug_enabled,
):
    engine_setup(
        ansible_engine,
        ansible_inventory,
        engine_ip,
        engine_hostname,
        ssh_key_path=ssh_key_file,
        answer_file_path=engine_answer_file_path,
        ovirt_engine_setup_offline='true',
        ovirt_engine_setup_engine_configs=[
            {'key': 'VdsLocalDisksLowFreeSpace', 'value': '400'},
            {'key': 'OvfUpdateIntervalInMinutes', 'value': '10'},
            {'key': 'ServerRebootTimeout', 'value': '150'},
        ],
    )
    # Work around https://gitlab.com/qemu-project/qemu/-/issues/641.
    # TODO: Remove when fixed.
    ansible_engine.shell(
        '/usr/share/ovirt-engine/dbscripts/engine-psql.sh '
        '-c '
        "\"select fn_db_update_config_value"
        "('NumOfPciExpressPorts','12','general');\""
    )
    ansible_engine.shell('ss -anp')

    ansible_engine.systemd(name='ovirt-engine-notifier', state='started')
    ansible_engine.systemd(name='ovirt-engine', state='started')
    ansible_engine.systemd(name='ovirt-engine-dwhd', state='started')
