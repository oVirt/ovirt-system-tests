#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import pytest

from ost_utils.deployment_utils import package_mgmt


@pytest.fixture(scope="session", autouse=True)
def check_installed_packages(all_hostnames):
    package_mgmt.check_installed_packages(all_hostnames)
