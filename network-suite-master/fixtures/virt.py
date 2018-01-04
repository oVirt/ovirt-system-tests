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

from fixtures import providers

from lib import storagelib
from lib import templatelib


CIRROS_IMAGE_NAME = 'CirrOS 0.3.5 for x86_64'
CIRROS_TEMPLATE_NAME = 'Cirros_0_3_5'


@pytest.fixture(scope='session')
def cirros_template(system, ovirt_image_repo, default_cluster,
                    default_storage_domain):
    ovirt_image_sd = storagelib.StorageDomain(system)
    ovirt_image_sd.import_by_name(providers.OVIRT_IMAGE_REPO_NAME)

    default_storage_domain.import_image(
        default_cluster, ovirt_image_sd, CIRROS_IMAGE_NAME,
        template_name=CIRROS_TEMPLATE_NAME
    )

    templatelib.wait_for_template_ok_status(system, CIRROS_TEMPLATE_NAME)
