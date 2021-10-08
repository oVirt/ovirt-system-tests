#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import pytest


@pytest.fixture(scope="session")
def root_password():
    # TODO: read it properly
    return "123456"
