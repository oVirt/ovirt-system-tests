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

import nose.tools as nt
from ovirtlago import testlib


@testlib.with_ovirt_prefix
def test_initialize_engine(prefix):
    engine = prefix.virt_env.engine_vm()

    answer_file_src = os.path.join(
        os.environ.get('SUITE'),
        'engine-answer-file.conf'
    )
    engine.copy_to(
        answer_file_src,
        '/tmp/answer-file',
    )

    result = engine.ssh(
        [
            'engine-setup',
            '--config-append=/tmp/answer-file',
        ],
    )
    nt.eq_(
        result.code, 0, 'engine-setup failed. Exit code is %s' % result.code
    )

    testlib.assert_true_within_long(
        lambda: engine.service('ovirt-engine').alive()
    )

# Change the timeout, requires engine restart

    result = engine.ssh(
        [
            'engine-config',
            '--set',
            'vdsConnectionTimeout=20',
        ],
    )
    nt.eq_(
        result.code, 0, 'engine-config failed. Exit code is %s' % result.code
    )

    result = engine.ssh(
        [
            "su",
            "postgres",
            "-c",
            '"psql engine -c \\\"update vdc_options set option_value=15 '
            'where option_name=\'SetupNetworksPollingTimeout\';\\\""',
        ],
    )
    nt.eq_(
        result.code, 0, 'DB change failed. Exit code is %s' % result.code
    )

    engine.service('ovirt-engine')._request_stop()
    testlib.assert_true_within_long(
        lambda: not engine.service('ovirt-engine').alive()
    )
    engine.service('ovirt-engine')._request_start()
    testlib.assert_true_within_long(
        lambda: engine.service('ovirt-engine').alive()
    )
