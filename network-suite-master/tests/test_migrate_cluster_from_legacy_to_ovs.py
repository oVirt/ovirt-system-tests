#
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
from lib import clusterlib
from lib import hostlib

from testlib import suite


pytestmark = suite.SKIP_SUITE_42


def test_migrate_cluster_from_legacy_to_ovs(
        host_1_up, system, default_data_center):

    with clusterlib.cluster(
            system, default_data_center, 'ovs-cluster') as ovs_cluster:
        ovs_cluster.set_network_switch_type(clusterlib.SwitchType.OVS)

        with hostlib.change_cluster(host_1_up, ovs_cluster):
            host_1_up.sync_all_networks()
            assert host_1_up.networks_in_sync()

        host_1_up.sync_all_networks()
        assert host_1_up.networks_in_sync()
