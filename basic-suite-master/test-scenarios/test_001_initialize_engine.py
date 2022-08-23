#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from __future__ import absolute_import

from ost_utils.ansible.collection import engine_setup


def test_initialize_engine(
    ansible_engine,
    ansible_inventory,
    engine_ip,
    engine_hostname,
    ssh_key_file,
    engine_answer_file_path,
):
    ansible_engine.shell(
        '/usr/share/ovirt-engine/setup/bin/ovirt-engine-provisiondb '
        '--otopi-environment="'
        'OVESETUP_PROVISIONDB_CONFIG/provisionDb=bool:True '
        'OVESETUP_PROVISIONDB_CONFIG/provisionUser=bool:True '
        'OVESETUP_PROVISION_DB/database=str:engine '
        'OVESETUP_PROVISION_DB/user=str:engine '
        'OVESETUP_PROVISION_DB/password=str:badpass-5"'
    )
    ansible_engine.shell(
        '/usr/share/ovirt-engine/setup/bin/ovirt-engine-provisiondb '
        '--otopi-environment="'
        'OVESETUP_PROVISIONDB_CONFIG/provisionDb=bool:True '
        'OVESETUP_PROVISIONDB_CONFIG/provisionUser=bool:True '
        'OVESETUP_PROVISION_DB/database=str:ovirt_engine_history '
        'OVESETUP_PROVISION_DB/user=str:ovirt_engine_history '
        'OVESETUP_PROVISION_DB/password=str:badpass-4"'
    )
    ansible_engine.shell(
        '/usr/share/ovirt-engine/setup/bin/ovirt-engine-provisiondb '
        '--otopi-environment="'
        'OVESETUP_PROVISIONDB_CONFIG/provisionDb=bool:False '
        'OVESETUP_PROVISIONDB_CONFIG/addToPGHBA=bool:True '
        'OVESETUP_PROVISIONDB_CONFIG/grantReadOnly=bool:True '
        'OVESETUP_PROVISIONDB_CONFIG/provisionUser=bool:True '
        'OVESETUP_PROVISION_DB/database=str:ovirt_engine_history '
        'OVESETUP_PROVISION_DB/user=str:ovirt_engine_history_grafana '
        'OVESETUP_PROVISION_DB/password=str:badpass-6"'
    )
    ansible_engine.shell(
        '/usr/share/ovirt-engine/setup/bin/ovirt-engine-provisiondb '
        '--otopi-environment="'
        'OVESETUP_PROVISIONDB_CONFIG/provisionDb=bool:True '
        'OVESETUP_PROVISIONDB_CONFIG/provisionUser=bool:True '
        'OVESETUP_PROVISION_DB/database=str:ovirt_engine_keycloak '
        'OVESETUP_PROVISION_DB/user=str:ovirt_engine_keycloak '
        'OVESETUP_PROVISION_DB/password=str:badpass-7"'
    )
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
