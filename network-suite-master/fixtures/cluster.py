# Copyright 2017 Red Hat, Inc.
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

from ovirtlib import clusterlib


@pytest.fixture(scope='session', autouse=True)
def default_cluster(system):
    DEFAULT_NAME = 'Default'
    cluster = clusterlib.Cluster(system)
    cluster.import_by_name(DEFAULT_NAME)
    return cluster


@pytest.fixture(scope='session')
def ovs_cluster(system, default_data_center):
    OVS_CLUSTER_NAME = 'ovs-cluster'
    with clusterlib.cluster(
            system, default_data_center, OVS_CLUSTER_NAME) as ovs_cluster:
        ovs_cluster.set_network_switch_type(clusterlib.SwitchType.OVS)
        yield ovs_cluster
