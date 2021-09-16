#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import pytest

from ovirtlib import datacenterlib


@pytest.fixture(scope='session', autouse=True)
def default_data_center(system):
    DEFAULT_NAME = 'Default'
    dc = datacenterlib.DataCenter(system)
    dc.import_by_name(DEFAULT_NAME)
    return dc


@pytest.fixture(scope='session')
def data_centers_service(system):
    return system.data_centers_service
