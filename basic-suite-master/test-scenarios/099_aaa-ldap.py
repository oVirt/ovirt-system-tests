#
# Copyright 2014 Red Hat, Inc.
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

import nose.tools as nt
import os
import tempfile

from ovirtsdk.xml import params
import ovirtsdk4.types as types

from ovirtlago import testlib

import test_utils

# AAA
AAA_LDAP_USER = 'user1'
AAA_LDAP_GROUP = 'mygroup'
AAA_LDAP_AUTHZ_PROVIDER = 'lago.local-authz'
HOSTNAME_389DS = testlib.get_prefixed_name('engine')


@testlib.with_ovirt_prefix
def add_ldap_provider(prefix):
    engine = prefix.virt_env.engine_vm()
    machine_389ds = prefix.virt_env.get_vm(HOSTNAME_389DS)

    answer_file_src = os.path.join(
        os.environ.get('SUITE'),
        'aaa-ldap-answer-file.conf'
    )

    with open(answer_file_src, 'r') as f:
        content = f.read()
        content = content.replace('@389DS_IP@', machine_389ds.ip())

    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(content)
    engine.copy_to(temp.name, '/root/aaa-ldap-answer-file.conf')
    os.unlink(temp.name)

    result = machine_389ds.ssh(
        [
            'systemctl',
            'start',
            'dirsrv@lago',
        ],
    )
    nt.eq_(
        result.code, 0, 'Failed to start LDAP server. Exit code %s' % result.code
    )

    result = engine.ssh(
        [
            'ovirt-engine-extension-aaa-ldap-setup',
            '--config-append=/root/aaa-ldap-answer-file.conf',
            '--log=/var/log/ovirt-engine-extension-aaa-ldap-setup.log',
        ],
    )
    nt.eq_(
        result.code, 0, 'aaa-ldap-setup failed. Exit code is %s' % result.code
    )

    engine.service('ovirt-engine')._request_stop()
    testlib.assert_true_within_long(
        lambda: not engine.service('ovirt-engine').alive()
    )
    engine.service('ovirt-engine')._request_start()
    testlib.assert_true_within_long(
        lambda: engine.service('ovirt-engine').alive()
    )


@testlib.with_ovirt_api
def add_ldap_user(api):
    p = params.User(
        user_name=AAA_LDAP_USER,
        domain=params.Domain(
            name=AAA_LDAP_AUTHZ_PROVIDER
        ),
    )
    nt.assert_true(api.users.add(p))


@testlib.with_ovirt_api4
def add_ldap_group(api):
    engine = api.system_service()
    groups_service = engine.groups_service()
    with test_utils.TestEvent(engine, 149): # USER_ADD(149)
        groups_service.add(
            types.Group(
                name=AAA_LDAP_GROUP,
                domain=types.Domain(
                    name=AAA_LDAP_AUTHZ_PROVIDER
                ),
            ),
        )


_TEST_LIST = [
    add_ldap_provider,
    add_ldap_group,
    add_ldap_user,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
