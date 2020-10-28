#
# Copyright 2018-2020 Red Hat, Inc.
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
import contextlib

import contextlib2

from ovirtlib import clusterlib
from ovirtlib import hostlib
from ovirtlib import netattachlib
from ovirtlib import sshlib as ssh

ETH2 = 'eth2'


def test_sync_across_cluster(default_data_center, default_cluster,
                             host_0_up, host_1_up):

    cluster_hosts_up = (host_0_up, host_1_up)
    with clusterlib.new_assigned_network(
            'sync-net', default_data_center, default_cluster) as sync_net:
        with contextlib2.ExitStack() as stack:
            for i, host in enumerate(cluster_hosts_up):
                att_datum = create_attachment(sync_net, i)
                stack.enter_context(
                    hostlib.setup_networks(host, (att_datum,))
                )
                stack.enter_context(unsynced_host_network(host))
            default_cluster.sync_all_networks()
            for host in cluster_hosts_up:
                host.wait_for_networks_in_sync()


def create_attachment(network, i):
    ip_assign = netattachlib.StaticIpAssignment(
        addr='192.168.125.' + str(i + 2), mask='255.255.255.0'
    )
    att_datum = netattachlib.NetworkAttachmentData(network, ETH2, (ip_assign,))
    return att_datum


@contextlib.contextmanager
def unsynced_host_network(host_up):
    ENGINE_DEFAULT_MTU = 1500
    node = ssh.Node(address=host_up.address, password=host_up.root_password)
    node.set_mtu(ETH2, ENGINE_DEFAULT_MTU + 1)
    host_up.refresh_capabilities()
    try:
        yield
    finally:
        node = ssh.Node(
            address=host_up.address, password=host_up.root_password
        )
        node.set_mtu(ETH2, ENGINE_DEFAULT_MTU)
        host_up.refresh_capabilities()
