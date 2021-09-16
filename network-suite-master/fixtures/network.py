#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import pytest

from ovirtlib import netlib


@pytest.fixture(scope='session', autouse=True)
def ovirtmgmt_network(default_data_center):
    network = netlib.Network(default_data_center)
    network.import_by_name('ovirtmgmt')
    return network


@pytest.fixture(scope='session', autouse=True)
def ovirtmgmt_vnic_profile(system):
    vnic_profile = netlib.VnicProfile(system)
    vnic_profile.import_by_name(netlib.OVIRTMGMT)
    return vnic_profile
