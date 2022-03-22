#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import os
import re


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


def guest_os_image_name():
    return 'CirrOS 0.5.1 Custom for x86_64'


def transformed_guest_os_image_name():
    return re.sub('[ ()]', '_', guest_os_image_name())


def guest_os_glance_disk_name():
    return transformed_guest_os_image_name()[:12] + '_glance_disk'


def guest_os_template_name():
    return transformed_guest_os_image_name()[:12] + '_glance_template'
