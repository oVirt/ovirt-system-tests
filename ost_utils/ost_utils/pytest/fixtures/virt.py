#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
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
