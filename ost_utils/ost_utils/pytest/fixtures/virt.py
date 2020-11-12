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

import re

import pytest

CIRROS_IMAGE_NAME = 'CirrOS 0.5.1 Custom for x86_64'


@pytest.fixture(scope="session")
def cirros_image():
    return CIRROS_IMAGE_NAME


@pytest.fixture(scope="session")
def transformed_cirros_image(cirros_image):
    return re.sub('[ ()]', '_', cirros_image)


@pytest.fixture(scope="session")
def cirros_image_glance_disk_name(transformed_cirros_image):
    return transformed_cirros_image[:12] + '_glance_disk'


@pytest.fixture(scope="session")
def cirros_image_glance_template_name(transformed_cirros_image):
    return transformed_cirros_image[:12] + '_glance_template'
