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
from lib import providerlib


def test_import_network(ovn_network, default_ovn_provider,
                        default_data_center, default_cluster):
    openstack_network = providerlib.OpenStackNetwork(default_ovn_provider)
    openstack_network.import_by_id(str(ovn_network.id))
    ovirt_network = openstack_network.create_external_network(
        default_data_center)
    try:
        cluster_network = clusterlib.ClusterNetwork(default_cluster)
        cluster_network.assign(ovirt_network)
    finally:
        ovirt_network.remove()
