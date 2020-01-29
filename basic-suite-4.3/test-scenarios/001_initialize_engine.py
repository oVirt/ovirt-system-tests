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

import test_utils


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
    engine.ssh(
        [
            'ss',
            '-anp',
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

    # Remove YUM leftovers that are in /var/cache/yum/* - just takes up space.
    result = engine.ssh(
        [
            'rm',
            '-rf',
            '/var/cache/yum/*',
        ]
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


def _exec_engine_config(engine, key, value):
    result = engine.ssh(
        [
            'engine-config',
            '--set',
            '{0}={1}'.format(key, value),
        ],
    )
    nt.eq_(
        result.code,
        0,
        'setting {0}:{1} via engine-config failed with {2}'.format(key, value, result.code)
    )


@testlib.with_ovirt_prefix
def engine_config(prefix):
    engine = prefix.virt_env.engine_vm()

    _exec_engine_config(engine, 'VdsLocalDisksLowFreeSpace', '400')
    _exec_engine_config(engine, 'OvfUpdateIntervalInMinutes', '10')


@testlib.with_ovirt_prefix
def engine_restart(prefix):
    engine = prefix.virt_env.engine_vm()

    engine.service('ovirt-engine')._request_stop()
    testlib.assert_true_within_long(
        lambda: not engine.service('ovirt-engine').alive()
    )

    engine.service('ovirt-engine')._request_start()
    testlib.assert_true_within_long(
        lambda: engine.service('ovirt-engine').alive()
    )


_TEST_LIST = [
    initialize_engine,
    engine_config,
    engine_restart,
]


def test_gen():
    for t in test_utils.test_gen(_TEST_LIST, test_gen):
        yield t
