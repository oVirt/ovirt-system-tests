#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import contextlib

from fixtures.host import ETH2

from ovirtlib import clusterlib
from ovirtlib import hostlib
from ovirtlib import netattachlib
from ovirtlib import sshlib as ssh


def test_sync_across_cluster(default_data_center, default_cluster, host_0_up, host_1_up):

    cluster_hosts_up = (host_0_up, host_1_up)
    with clusterlib.new_assigned_network('sync-net', default_data_center, default_cluster) as sync_net:
        with contextlib.ExitStack() as stack:
            for host in cluster_hosts_up:
                net_attachment = netattachlib.NetworkAttachmentData(
                    sync_net, ETH2, (netattachlib.NO_V4, netattachlib.NO_V6)
                )
                stack.enter_context(hostlib.setup_networks(host, (net_attachment,)))
                stack.enter_context(unsynced_host_network(host))
            for host in cluster_hosts_up:
                host.wait_for_networks_out_of_sync((sync_net,))
            default_cluster.sync_all_networks()
            for host in cluster_hosts_up:
                host.wait_for_networks_in_sync()


@contextlib.contextmanager
def unsynced_host_network(host_up):
    ENGINE_DEFAULT_MTU = 1500
    node = ssh.Node(address=host_up.address, password=host_up.root_password)
    node.set_mtu(ETH2, ENGINE_DEFAULT_MTU + 1)
    host_up.refresh_capabilities()
    try:
        yield
    finally:
        node = ssh.Node(address=host_up.address, password=host_up.root_password)
        node.set_mtu(ETH2, ENGINE_DEFAULT_MTU)
        host_up.refresh_capabilities()
