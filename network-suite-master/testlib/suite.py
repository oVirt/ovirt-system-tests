#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import os

import logging
from packaging.version import Version

import ovirtsdk4
import pytest

SUITE = os.environ['SUITE']
SUITE_VERSION = SUITE.split('-')[-1]
LOGGER = logging.getLogger(__name__)


def suite_dir():
    return os.path.join(os.environ['OST_REPO_ROOT'], os.environ['SUITE'])


def playbook_dir():
    return os.path.join(suite_dir(), 'ansible')


def xfail_suite_master(reason, raises=None):
    return pytest.mark.xfail(
        condition=SUITE.endswith('master'),
        reason=reason,
        raises=raises,
        run=False,
    )


def xfail_suite_43(reason):
    return pytest.mark.xfail(condition=SUITE.endswith('4.3'), reason=reason, run=False)


def skip_suites_below(version):
    skip = is_suite_below(version)
    return pytest.mark.skipif(skip, reason=_skip_reason(skip, f'suite version {version}'))


def is_suite_below(version):
    return _compare_versions(SUITE_VERSION, version) < 0


def skip_sdk_below(version):
    skip = _is_sdk_below(version)
    return pytest.mark.skipif(skip, reason=_skip_reason(skip, f'SDK version {version}'))


def _is_sdk_below(version):
    return _compare_versions(ovirtsdk4.version.VERSION, version) < 0


def _skip_reason(skip, version):
    return f'Only supported since {version}' if skip else ''


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
    if Version(runtime_version) < Version(candidate_version):
        return -1
    return 1
