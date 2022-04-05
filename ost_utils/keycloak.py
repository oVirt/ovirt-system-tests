#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#


import ovirtsdk4 as sdk4

# Keycloak
KCADM = 'KC_OPTS="-Dcom.redhat.fips=false " /usr/share/ovirt-engine-wildfly/bin/kcadm.sh'


def setup_truststore(ansible_engine):
    ansible_engine.shell(f'{KCADM} config truststore --trustpass mypass /etc/pki/ovirt-engine/.truststore')


def authenticate(ansible_engine, auth_server_url, realm, user, password):
    ansible_engine.shell(
        f'{KCADM} config credentials '
        f'--server {auth_server_url} '
        f'--realm {realm} '
        f'--user {user} '
        f'--password {password}'
    )


def create_user(ansible_engine, realm, username, password):
    ansible_engine.shell(f'{KCADM} create users -r {realm} -s username={username} -s enabled=true')
    ansible_engine.shell(f'{KCADM} set-password -r {realm} --username {username} --new-password {password}')


def activate_user(engine_api_url, username, password, profile):
    # In order to sync Keycloak user with Engine db we need at least an attempt to authenticate
    # and access some protected resources
    api = sdk4.Connection(
        url=engine_api_url,
        username=f'{username}@{profile}',
        password=password,
        insecure=True,
        debug=True,
    )
    api.test(raise_exception=False)


def resolve_user_id(engine_api, username):
    users = engine_api.system_service().users_service().list()
    for u in users:
        if u.principal == username:
            return u.id
    return None
