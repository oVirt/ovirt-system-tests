#
# Copyright 2017 Red Hat, Inc.
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

from ovirtlago import testlib


@testlib.with_ovirt_prefix
def analyze_postgres(prefix):
    """
        analyze postgres logs will use pgbadger, pgcluu (and possibly more in the tools
        in the future) to create a static html reports and csv data.
        Report will be created under the log directory of pg - maybe subjected to changes
        in the future.
        TODO - add test based on the audit output, like fail the test if there are missing indexes
    """

    engine = prefix.virt_env.engine_vm()

    analyze_script = os.path.join(
        os.environ.get('SUITE'),
        '../common/test-scenarios-files/analyze_postgresql.sh'
    )
    engine.copy_to(analyze_script, '/root')

    result = engine.ssh(
        [
            '/root/analyze_postgresql.sh'
        ],
    )
    nt.eq_(
        result.code, 0, 'Failed to perform the postgres analysis.'
                        ' Exit code is %s' % result.code
    )


_TEST_LIST = [
    analyze_postgres,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
