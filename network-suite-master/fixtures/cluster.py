#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
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
    with clusterlib.cluster(system, default_data_center, OVS_CLUSTER_NAME) as ovs_cluster:
        ovs_cluster.network_switch_type = clusterlib.SwitchType.OVS
        yield ovs_cluster
