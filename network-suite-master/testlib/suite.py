#
# Copyright 2018 Red Hat, Inc.
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
import contextlib
import os

import pytest


SUITE_NAME = os.path.split(os.environ['SUITE'])[-1]


SKIP_SUITE_42 = pytest.mark.skipif(SUITE_NAME.endswith('4.2'),
                                   reason='Not supported on 4.2 suite')

SKIP_SUITE_43 = pytest.mark.skipif(SUITE_NAME.endswith('4.3'),
                                   reason='Not supported on 4.3 suite')


def XFAIL_SUITE_MASTER(reason):
    return pytest.mark.xfail(
            condition=SUITE_NAME.endswith('master'),
            reason=reason,
            run=False
            )


def is_master():
    return SUITE_NAME.endswith('master')


@contextlib.contextmanager
def collect_artifacts(env, artifacts_path, module_name):
    try:
        yield
    finally:
        p = os.path.join(artifacts_path, module_name)
        os.makedirs(p)
        env.collect_artifacts(output_dir=p, ignore_nopath=True)
