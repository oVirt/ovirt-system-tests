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
from __future__ import absolute_import

import os
import socket

from tempfile import NamedTemporaryFile
from ovirtlago import testlib

import test_utils

from ost_utils.pytest.fixtures import prefix
from ost_utils.pytest.fixtures.ansible import ansible_engine
from ost_utils.pytest.fixtures.ansible import ansible_hosts


def test_check_ansible_connectivity(ansible_engine, ansible_hosts):
    ansible_engine.ping()
    ansible_hosts.ping()


def test_initialize_engine(prefix, ansible_engine):
    engine = prefix.virt_env.engine_vm()

    answer_file_src = os.path.join(
        os.environ.get('SUITE'), 'engine-answer-file.conf'
    )

    ansible_engine.copy(
        src=answer_file_src,
        dest='/tmp/answer-file',
    )

    nics = engine.nics()
    nets = prefix.get_nets()
    engine_ip = [
        nic.get('ip') for nic in nics if nets[nic.get('net')].is_management()
    ]

    host_name = socket.getfqdn()
    host_ip = socket.gethostbyname(host_name)

    with NamedTemporaryFile(mode='w', delete=False) as sso_conf:
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
            '--offline',
        ],
    )
    engine.ssh(
        [
            'ss',
            '-anp',
        ],
    )
    assert result.code == 0, \
        'engine-setup failed. Exit code is %s' % result.code

    result = engine.ssh(
        [
            'systemctl',
            'start',
            'ovirt-engine-notifier',
        ],
    )
    assert result.code == 0, \
        'engine-ovirt-notifier failed. Exit code is %s' % result.code

    # Remove YUM leftovers that are in /var/cache/[dnf/yum]* - free disk space.
    result = engine.ssh(
        [
            'rm',
            '-rf',
            '/var/cache/yum/*',
            '/var/cache/dnf/*',
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
    assert result.code == 0, \
        'setting {0}:{1} via engine-config failed with {2}'.format(
            key, value, result.code)


def test_engine_config(prefix):
    engine = prefix.virt_env.engine_vm()

    _exec_engine_config(engine, 'VdsLocalDisksLowFreeSpace', '400')
    _exec_engine_config(engine, 'OvfUpdateIntervalInMinutes', '10')


def test_engine_restart(prefix):
    engine = prefix.virt_env.engine_vm()

    engine.service('ovirt-engine')._request_stop()
    testlib.assert_true_within_long(
        lambda: not engine.service('ovirt-engine').alive()
    )

    engine.service('ovirt-engine')._request_start()
    testlib.assert_true_within_long(
        lambda: engine.service('ovirt-engine').alive()
    )
