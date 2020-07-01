#
# Copyright 2020 Red Hat, Inc.
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
from distutils.version import LooseVersion
import os

import ovirtsdk4
import pytest


SUITE_NAME = os.path.split(os.environ['SUITE'])[-1]


def skip_suites_below(version):
    if is_master():
        reason = 'Always run master'
        skip = False
    else:
        skip = LooseVersion(SUITE_NAME.split('-')[-1]) < LooseVersion(version)
        reason = 'Only supported upwards of suite {}'.format(version)
    return pytest.mark.skipif(skip, reason=reason)


def xfail_suite_master(reason):
    return pytest.mark.xfail(
            condition=SUITE_NAME.endswith('master'),
            reason=reason,
            run=False
            )


def xfail_suite_43(reason):
    return pytest.mark.xfail(
            condition=SUITE_NAME.endswith('4.3'),
            reason=reason,
            run=False
            )


def skip_sdk_below(version):
    if _is_sdk_below(version):
        skip = True
        reason = 'Only supported upwards of SDK {}'.format(version)
    else:
        reason = 'SDK version is fine'
        skip = False
    return pytest.mark.skipif(skip, reason=reason)


def _is_sdk_below(version):
    return _compare_versions(ovirtsdk4.version.VERSION, version) < 0


def _compare_versions(runtime_version, candidate_version):
    """
    :param runtime_version: version number as string or 'master'
    :param candidate_version: version number as string or 'master'
    :return: -1 if runtime_version is smaller
              0 if versions are equal
              1 if runtime_version version is larger
    """
    if candidate_version == runtime_version:
        return 0
    if runtime_version == 'master':
        return 1
    if candidate_version == 'master':
        return -1
    if LooseVersion(runtime_version) < LooseVersion(candidate_version):
        return -1
    return 1


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
