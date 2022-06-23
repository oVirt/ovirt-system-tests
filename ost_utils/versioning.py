#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import os


_DC_VERSION = '4.7'


def cluster_version():
    version = os.getenv('OST_DC_VERSION', _DC_VERSION).split('.')
    return [int(v) for v in version]


def cluster_version_ok(major, minor):
    current = cluster_version()
    return current[0] > major or (current[0] == major and current[1] >= minor)


def require_version(major, minor):
    if cluster_version_ok(major, minor):
        return lambda test: test
    else:

        def skipped(test):
            # TODO: Any way to log that test.__name__ has been skipped?
            return lambda *args, **kwargs: True

        return skipped
