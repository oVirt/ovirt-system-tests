#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import functools

from ovirtsdk4.types import DataCenter, Network, NetworkLabel, Vlan

from ost_utils import assert_utils
from ost_utils import network_utils
from ost_utils import test_utils
from ost_utils import utils


# Network
NETWORK_LABEL = 'NETWORK_LABEL'
LABELED_NET_NAME = 'Labeled_Network'
LABELED_NET_VLAN_ID = 600


def _host_is_attached_to_network(engine, host, network_name, dc_name):
    try:
        network_utils.get_network_attachment(engine, host, network_name, dc_name)
    except StopIteration:  # there is no attachment of the network to the host
        return False

    return True


def test_assign_hosts_network_label(system_service, hosts_service, ost_cluster_name):
    """
    Assigns NETWORK_LABEL to first network interface of every host in cluster
    """

    def _assign_host_network_label(host):
        host_service = hosts_service.host_service(id=host.id)
        nics_service = host_service.nics_service()
        nics = sorted(nics_service.list(), key=lambda n: n.name)
        assert len(nics) >= 1
        nic = nics[0]
        nic_service = nics_service.nic_service(id=nic.id)
        labels_service = nic_service.network_labels_service()
        return labels_service.add(NetworkLabel(id=NETWORK_LABEL, host_nic=nic))

    hosts = test_utils.hosts_in_cluster_v4(system_service, ost_cluster_name)
    vec = utils.func_vector(_assign_host_network_label, [(h,) for h in hosts])
    vt = utils.VectorThread(vec)
    vt.start_all()
    assert all(vt.join_all())


def test_add_labeled_network(networks_service, ost_dc_name):
    """
    Creates a labeled network
    """
    # create network
    labeled_net = Network(
        name=LABELED_NET_NAME,
        data_center=DataCenter(name=ost_dc_name),
        description=f'Labeled network on VLAN {LABELED_NET_VLAN_ID}',
        usages=[],
        # because only one non-VLAN network, here 'ovirtmgmt', can be assigned
        # to each nic, this additional network has to be a VLAN network
        # NOTE: we have added three more NICs since creating this test
        vlan=Vlan(id=LABELED_NET_VLAN_ID),
    )
    net = networks_service.add(labeled_net)
    assert net

    network_service = networks_service.network_service(id=net.id)
    labels_service = network_service.network_labels_service()

    # assign label to the network
    assert labels_service.add(NetworkLabel(id=NETWORK_LABEL))
    assert len([label for label in labels_service.list() if label.id == NETWORK_LABEL]) == 1


def test_assign_labeled_network(
    system_service,
    networks_service,
    hosts_service,
    ost_dc_name,
    ost_cluster_name,
):
    """
    Adds the labeled network to the cluster and asserts the hosts are attached
    """
    labeled_net = networks_service.list(search=f'name={LABELED_NET_NAME}')[0]

    # the logical network will be automatically assigned to all host network
    # interfaces with that label asynchronously

    cluster_service = test_utils.get_cluster_service(system_service, ost_cluster_name)
    assert cluster_service.networks_service().add(labeled_net)

    for host in test_utils.hosts_in_cluster_v4(system_service, ost_cluster_name):
        host_service = hosts_service.host_service(id=host.id)
        assert assert_utils.true_within_short(
            lambda: _host_is_attached_to_network(
                system_service,
                host_service,
                LABELED_NET_NAME,
                ost_dc_name,
            )
        )
