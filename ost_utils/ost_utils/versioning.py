#
# Copyright 2020-2021 Red Hat, Inc.
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
import re


_DC_VERSION = '4.6'


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
