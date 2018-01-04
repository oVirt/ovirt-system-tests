# Copyright 2017-2018 Red Hat, Inc.
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

from lib import netlib


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
