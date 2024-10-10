#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from __future__ import absolute_import

import os
import tempfile

import ovirtsdk4.types as types
import pytest

from ost_utils import engine_utils

# AAA
from ost_utils.pytest.fixtures.ansible import ansible_storage

AAA_LDAP_USER = 'user1'
AAA_LDAP_GROUP = 'mygroup'
AAA_LDAP_AUTHZ_PROVIDER = 'lago.local-authz'


@pytest.fixture(scope="session")
def ansible_machine_389ds(ansible_storage):
    return ansible_storage


@pytest.fixture(scope="session")
def machine_389ds_fqdn(ansible_machine_389ds):
    return ansible_machine_389ds.shell('hostname -f')['stdout']


def test_add_ldap_provider(
    root_dir,
    ansible_engine,
    ansible_machine_389ds,
    machine_389ds_fqdn,
    engine_restart,
    ost_images_distro,
):
    # FIXME remove once we get LDAP working on el9 storage image
    if ost_images_distro != 'rhel8':
        pytest.skip('Testing only on rhel8 images.')
    answer_file_src = os.path.join(root_dir, 'common/answer-files/aaa-ldap-answer-file.conf')

    with open(answer_file_src, 'r') as f:
        content = f.read()
        content = content.replace('@389DS_IP@', machine_389ds_fqdn)

    with tempfile.NamedTemporaryFile(mode='w') as temp:
        temp.write(content)
        temp.flush()
        os.fsync(temp.fileno())
        ansible_engine.copy(src=temp.name, dest='/root/aaa-ldap-answer-file.conf')

    ansible_machine_389ds.systemd(name='dirsrv@lago', state='started')

    ansible_engine.shell(
        'ovirt-engine-extension-aaa-ldap-setup '
        '--config-append=/root/aaa-ldap-answer-file.conf '
        '--log=/var/log/ovirt-engine-extension-aaa-ldap-setup.log'
    )

    engine_restart()


def test_add_ldap_group(engine_api, ost_images_distro):
    # FIXME remove once we get LDAP working on el9 storage image
    if ost_images_distro != 'rhel8':
        pytest.skip('Testing only on rhel8 images.')
    engine = engine_api.system_service()
    groups_service = engine.groups_service()
    with engine_utils.wait_for_event(engine, 149):  # USER_ADD(149)
        groups_service.add(
            types.Group(
                name=AAA_LDAP_GROUP,
                domain=types.Domain(name=AAA_LDAP_AUTHZ_PROVIDER),
            ),
        )


def test_add_ldap_user(engine_api, ost_images_distro):
    # FIXME remove once we get LDAP working on el9 storage image
    if ost_images_distro != 'rhel8':
        pytest.skip('Testing only on rhel8 images.')
    engine = engine_api.system_service()
    users_service = engine.users_service()
    with engine_utils.wait_for_event(engine, 149):  # USER_ADD(149)
        users_service.add(
            types.User(
                user_name=AAA_LDAP_USER,
                domain=types.Domain(name=AAA_LDAP_AUTHZ_PROVIDER),
            ),
        )
