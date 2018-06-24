# -*- coding: utf-8 -*-
#
# Copyright 2014, 2017 Red Hat, Inc.
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
import subprocess
from ovirtlago import testlib


@testlib.with_ovirt_prefix
def install_origin_and_flex(prefix):
    engine = prefix.virt_env.engine_vm()
    engine_ip = engine.ip()
    engine_pass = engine.metadata['ovirt-engine-password']
    user_vars = os.path.join(os.environ['SUITE'], 'user_vars.yaml')

    exit_code = subprocess.call([
        'docker', 'run',
        '--rm',
        '--network', 'host',
        '--add-host', 'engine:{}'.format(engine_ip),
        '-e', 'ENGINE_IP={}'.format(engine_ip),
        '-e', 'ENGINE_URL={}'.format('https://engine/ovirt-engine/api'),
        '-e', 'ENGINE_USER={}'.format('admin@internal'),
        '-e', 'ENGINE_PASS={}'.format(engine_pass),
        '-v', '{}:/root/user_vars.yaml'.format(user_vars),
        'docker.io/rgolangh/ovirt-openshift-extensions-ci',
    ])

    if exit_code > 0:
        raise RuntimeError('openshift installation failed')


_TEST_LIST = [
    install_origin_and_flex,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
