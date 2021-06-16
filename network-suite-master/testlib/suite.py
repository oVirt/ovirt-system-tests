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
from distutils.version import LooseVersion
import os

import ovirtsdk4
import pytest

from testlib import address_family

SUITE_NAME = os.path.split(os.environ['SUITE'])[-1]
SUITE_VERSION = SUITE_NAME.split('-')[-1]


def af():
    """
    The address family to use for all connections in the session.
    IP_VERSION environment variable expected values: '4' or '6'.
    """
    try:
        return address_family.AF(os.environ['IP_VERSION'])
    except KeyError:
        return address_family.AF('4')


def xfail_suite_master(reason, raises=None):
    return pytest.mark.xfail(
            condition=SUITE_NAME.endswith('master'),
            reason=reason,
            raises=raises,
            run=False
            )


def xfail_suite_43(reason):
    return pytest.mark.xfail(
            condition=SUITE_NAME.endswith('4.3'),
            reason=reason,
            run=False
            )


def skip_suites_below(version):
    skip = is_suite_below(version)
    return pytest.mark.skipif(
        skip, reason=_skip_reason(skip, 'suite version {}'.format(version))
    )


def is_suite_below(version):
    return _compare_versions(SUITE_VERSION, version) < 0


def skip_sdk_below(version):
    skip = _is_sdk_below(version)
    return pytest.mark.skipif(
        skip, reason=_skip_reason(skip, 'SDK version {}'.format(version))
    )


def _is_sdk_below(version):
    return _compare_versions(ovirtsdk4.version.VERSION, version) < 0


def _skip_reason(skip, version):
    return 'Only supported since {}'.format(version) if skip else ''


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
