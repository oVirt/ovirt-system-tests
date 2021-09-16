#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import pytest

from ovirtlib.system import SDKSystemRoot


@pytest.fixture(scope='session')
def system(api):
    sdk_system = SDKSystemRoot()
    sdk_system.import_conn(api)
    return sdk_system
