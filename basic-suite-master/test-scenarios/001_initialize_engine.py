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
import os
import socket

from tempfile import NamedTemporaryFile
import nose.tools as nt
from ovirtlago import testlib


@testlib.with_ovirt_prefix
def initialize_engine(prefix):
    engine = prefix.virt_env.engine_vm()

    answer_file_src = os.path.join(
        os.environ.get('SUITE'), 'engine-answer-file.conf'
    )
    engine.copy_to(
        answer_file_src,
        '/tmp/answer-file',
    )

    nics = engine.nics()
    nets = prefix.get_nets()
    engine_ip = [
        nic.get('ip') for nic in nics if nets[nic.get('net')].is_management()
    ]

    host_name = socket.getfqdn()
    host_ip = socket.gethostbyname(host_name)

    with NamedTemporaryFile(delete=False) as sso_conf:
        sso_conf.write(
            (
                'SSO_ALTERNATE_ENGINE_FQDNS='
                '"${{SSO_ALTERNATE_ENGINE_FQDNS}} {0} {1} {2}"\n'
            ).format(engine_ip.pop(), host_name, host_ip)
        )

    fqdn_conf = '/etc/ovirt-engine/engine.conf.d/99-custom-fqdn.conf'
    engine.copy_to(sso_conf.name, fqdn_conf)
    engine.ssh(['chmod', '644', fqdn_conf])
    result = engine.ssh(
        [
            'engine-setup',
            '--config-append=/tmp/answer-file',
            '--accept-defaults',
        ],
    )
    nt.eq_(
        result.code, 0, 'engine-setup failed. Exit code is %s' % result.code
    )

    result = engine.ssh(
        [
            'systemctl',
            'start',
            'ovirt-engine-notifier',
        ],
    )
    nt.eq_(
        result.code, 0, 'engine-ovirt-notifier failed. Exit code is %s' % result.code
    )

    # Remove YUM leftovers that are in /dev/shm/* - just takes up memory.
    result = engine.ssh(
        [
            'rm',
            '-rf',
            '/dev/shm/yum',
            '/dev/shm/yumdb',
            '/dev/shm/*.rpm',
        ]
    )

    # TODO: set iSCSI, NFS, LDAP ports in firewall & re-enable it.
    result = engine.ssh([
        'systemctl',
        'stop',
        'firewalld',
    ], )
    nt.eq_(
        result.code, 0, 'firwalld not stopped. Exit code is %s' % result.code
    )

    testlib.assert_true_within_long(
        lambda: engine.service('ovirt-engine').alive()
    )

    testlib.assert_true_within_short(
        lambda: engine.service('ovirt-engine-dwhd').alive()
    )
    testlib.assert_true_within_short(
        lambda: engine.service('ovirt-engine-notifier').alive()
    )


@testlib.with_ovirt_prefix
def engine_config(prefix):
    engine = prefix.virt_env.engine_vm()

    result = engine.ssh(
        [
            'engine-config',
            '--set',
            'VdsLocalDisksLowFreeSpace=400',
        ],
    )
    nt.eq_(
        result.code, 0, 'engine-config failed. Exit code is %s' % result.code
    )


_TEST_LIST = [
    initialize_engine,
    engine_config,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
