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

import pytest

from ost_utils import versioning


@pytest.fixture(scope="session")
def cirros_image():
    return versioning.guest_os_image_name()


@pytest.fixture(scope="session")
def transformed_cirros_image():
    return versioning.transformed_guest_os_image_name()


@pytest.fixture(scope="session")
def cirros_image_glance_disk_name():
    return versioning.guest_os_glance_disk_name()


@pytest.fixture(scope="session")
def cirros_image_glance_template_name():
    return versioning.guest_os_template_name()


@pytest.fixture(scope="session")
def cirros_image_disk_name():
    return 'cirros_disk'


@pytest.fixture(scope="session")
def cirros_image_template_name():
    return 'cirros_template'
