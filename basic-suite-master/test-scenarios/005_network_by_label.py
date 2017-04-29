#
# Copyright 2016-2017 Red Hat, Inc.
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

from lago import utils
import nose.tools as nt
from ovirtlago import testlib
from ovirtsdk.xml import params
from ovirtsdk4.types import NetworkLabel

import test_utils


# DC/Cluster
DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

# Network
NETWORK_LABEL = 'NETWORK_LABEL'
LABELED_NET_NAME = 'Labeled_Network'
LABELED_NET_VLAN_ID = 600


@testlib.with_ovirt_api4
def assign_hosts_network_label(api):
    """
    Assigns NETWORK_LABEL to first network interface of every host in cluster
    """
    engine = api.system_service()

    def _assign_host_network_label(host):
        host_service = engine.hosts_service().host_service(id=host.id)
        nics = sorted(host_service.nics_service().list(),
                      key=lambda n: n.name)
        nt.assert_greater_equal(len(nics), 1)
        nic = nics[0]
        nic_service = host_service.nics_service().nic_service(id=nic.id)
        labels_service = nic_service.network_labels_service()
        return labels_service.add(
                NetworkLabel(
                    id=NETWORK_LABEL,
                    host_nic=nic
                )
            )

    hosts = test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME)
    vec = utils.func_vector(_assign_host_network_label, [(h,) for h in hosts])
    vt = utils.VectorThread(vec)
    vt.start_all()
    nt.assert_true(all(vt.join_all()))


@testlib.with_ovirt_api
def add_labeled_network(api):
    """
    Creates a labeled network
    """

    # create network
    labeled_net = params.Network(
        name=LABELED_NET_NAME,
        data_center=params.DataCenter(
            name=DC_NAME,
        ),
        description='Labeled network on VLAN {}'.format(LABELED_NET_VLAN_ID),
        usages=params.Usages(),
        # because only one non-VLAN network, here 'ovirtmgmt', can be assigned
        # to each nic, this additional network has to be a VLAN network
        vlan=params.VLAN(
            id=LABELED_NET_VLAN_ID,
        ),
    )
    net = api.networks.add(labeled_net)
    nt.assert_true(net)

    # assign label to the network
    nt.assert_true(
        net.labels.add(
            params.Label(
                id=NETWORK_LABEL
            )
        )
    )
    nt.assert_equal(
        len(
            net.labels.list(
                id=NETWORK_LABEL
            )
        ),
        1
    )


@testlib.with_ovirt_api
def assign_labeled_network(api):
    """
    Adds the labeled network to the cluster and asserts the hosts are attached
    """

    labeled_net = api.networks.get(name=LABELED_NET_NAME)

    def _host_is_in_labeled_network():
        for networkattachment in host.networkattachments.list():
            network = api.networks.get(id=networkattachment.network.get_id())
            if network.name == LABELED_NET_NAME:
                return True
        return False

    # the logical network will be automatically assigned to all host network
    # interfaces with that label asynchronously
    nt.assert_true(
        api.clusters.get(CLUSTER_NAME).networks.add(labeled_net)
    )

    for host in test_utils.hosts_in_cluster_v3(api, CLUSTER_NAME):
        testlib.assert_true_within_short(_host_is_in_labeled_network)


_TEST_LIST = [
    assign_hosts_network_label,
    add_labeled_network,
    assign_labeled_network,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
