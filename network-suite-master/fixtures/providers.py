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
import pytest

from lib.providerlib import OpenStackImageProviders


OVIRT_IMAGE_REPO_NAME = 'ovirt-image-repository'
OVIRT_IMAGE_REPO_URL = 'http://glance.ovirt.org:9292/'


@pytest.fixture(scope='session')
def ovirt_image_repo(system):
    openstack_image_providers = OpenStackImageProviders(system)
    if openstack_image_providers.is_provider_available(OVIRT_IMAGE_REPO_NAME):
        openstack_image_providers.import_by_name(OVIRT_IMAGE_REPO_NAME)
    else:
        openstack_image_providers.create(name=OVIRT_IMAGE_REPO_NAME,
                                         url=OVIRT_IMAGE_REPO_URL)
        openstack_image_providers.wait_until_available()
