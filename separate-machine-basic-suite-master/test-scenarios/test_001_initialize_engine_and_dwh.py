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


def test_initialize_dwh(
    ansible_dwh,
    dwh_answer_file_path,
):
    # TODO Use engine_setup? Perhaps by adapting it to not require
    # all the parameters it requires now and are irrelevant for dwh?
    ansible_dwh.copy(
        src=dwh_answer_file_path,
        dest='/root/dwh-answer-file',
    )
    ansible_dwh.shell(
        f'engine-setup '
        '--accept-defaults '
        '--config-append=/root/dwh-answer-file '
        '--offline '
    )


def test_add_dwh_to_keycloak_redirect_uris_for_grafana(
    ansible_engine,
    engine_fqdn,
    engine_password,
    dwh_fqdn,
):
    def run_ansible_engine_kcadm(args):
        return ansible_engine.shell(
            'KC_OPTS=-Dcom.redhat.fips=false '
            '/usr/share/ovirt-engine-wildfly/bin/kcadm.sh '
            + args
        )

    # Set truststore, so that https works
    run_ansible_engine_kcadm(
        'config truststore '
        '--trustpass mypass /etc/pki/ovirt-engine/.truststore '
    )

    # Login
    run_ansible_engine_kcadm(
        'config credentials '
        f'--server https://{engine_fqdn}/ovirt-engine-auth '
        '--realm master '
        '--user admin '
        f'--password {engine_password} '
    )

    # Get the Id of the internal client. Various hard-coded strings here
    # must match relevant code/constants from ovirt-engine-keycloak.
    id_res = run_ansible_engine_kcadm(
        'get clients '
        '-r ovirt-internal '
        '-q clientId=ovirt-engine-internal '
        '--fields id '
        '--format csv'
    )
    id = id_res['stdout_lines'][0].strip('"')

    # Get current URIs
    current_uris_res = run_ansible_engine_kcadm(
        f'get clients/{id} '
        '-r ovirt-internal '
        '--fields redirectUris '
        '--format csv'
    )
    current_uris = current_uris_res['stdout_lines'][0]

    # Add dwh
    run_ansible_engine_kcadm(
        f'update clients/{id} '
        '-r ovirt-internal '
        f'-s redirectUris=\'[{current_uris}, "https://{dwh_fqdn}*"]\''
    )
