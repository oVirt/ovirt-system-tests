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
def tweak_db(prefix):
    engine = prefix.virt_env.engine_vm()

    tweak_db_file = os.path.join(
        os.environ.get('SUITE'),
        '../common/deploy-scripts/db_config_tweaks.sh'
    )
    engine.copy_to(tweak_db_file, '/root')

    result = engine.ssh(
        [
            '/root/db_config_tweaks.sh',
        ],
    )
    nt.eq_(
        result.code, 0, 'tweaking postgres configuration failed. Exit code is %s' % result.code
    )


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t


_TEST_LIST = [
        tweak_db,
]
