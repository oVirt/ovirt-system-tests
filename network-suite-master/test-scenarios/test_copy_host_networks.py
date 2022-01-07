#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from collections import namedtuple
import contextlib

import pytest

from fixtures.host import ETH1
from fixtures.host import ETH2
from fixtures.host import ETH3

from ovirtlib import clusterlib
from ovirtlib import joblib
from ovirtlib import hostlib
from ovirtlib.netattachlib import BondingData
from ovirtlib.netattachlib import NetworkAttachmentData as AttachData

from testlib import suite

BOND0 = 'bond0'

VM_NET_NAME = 'vm-net'
VLAN_10_NET_NAME = 'vlan-10-net'
VLAN_20_NET_NAME = 'vlan-20-net'
VLAN_30_NET_NAME = 'vlan-30-net'
VLAN_30_NET_NAME_1 = 'vlan-30-net-1'

Config = namedtuple('Config', ('attachments', 'bonds'))


@suite.skip_suites_below('4.4')
@suite.skip_sdk_below('4.4')
def test_copy_host_networks(configured_hosts):
    source_host = configured_hosts[0]
    destination_host = configured_hosts[1]

    destination_host.copy_networks_from(source_host)
    assert source_host.compare_nics_except_mgmt(destination_host, CopyHostComparator.compare)


@pytest.fixture(
    scope='function',
    params=[
        ('ovirtmgmt_only', 'ovirtmgmt_only'),
        ('vlan_and_nonvlan', 'single_network'),
        ('networks_and_bond_0', 'vlan_and_nonvlan'),
        ('networks_and_bond_1', 'networks_and_bond_0'),
        ('ovirtmgmt_only', 'networks_and_bond_1'),
        ('vlan_and_nonvlan', 'ovirtmgmt_only'),
        ('ovirtmgmt_only', 'vlan_and_nonvlan'),
        ('networks_and_bond_0', 'ovirtmgmt_only'),
    ],
    ids=[
        'copy_nothing_to_host_with_nothing',
        'copy_vlan_and_nonvlan_to_host_with_single_network',
        'copy_networks_and_bond_0_to_host_with_vlan_and_nonvlan',
        'copy_networks_and_bond_1_to_host_with_networks_and_bond_0',
        'copy_nothing_to_host_with_networks_and_bond_1',
        'copy_vlan_and_nonvlan_to_host_with_nothing',
        'copy_nothing_to_host_with_vlan_and_nonvlan',
        'copy_networks_and_bond_0_to_host_with_nothing',
    ],
)
def configured_hosts(request, host_config, host_0_up, host_1_up):
    SRC_CONF = request.param[0]
    DEST_CONF = request.param[1]

    setup_host_0 = hostlib.setup_networks(
        host_0_up,
        attach_data=host_config[SRC_CONF].attachments,
        bonding_data=host_config[SRC_CONF].bonds,
    )

    setup_host_1 = _setup_destination_host(
        host_1_up,
        attach_data=host_config[DEST_CONF].attachments,
        bonding_data=host_config[DEST_CONF].bonds,
    )

    with setup_host_0, setup_host_1:
        yield (host_0_up, host_1_up)


@pytest.fixture(scope='module')
def host_config(networks):
    return {
        'ovirtmgmt_only': Config((), ()),
        'single_network': Config((AttachData(networks[VM_NET_NAME], ETH1),), ()),
        'vlan_and_nonvlan': Config(
            (
                AttachData(networks[VLAN_10_NET_NAME], ETH1),
                AttachData(networks[VM_NET_NAME], ETH2),
            ),
            (),
        ),
        'networks_and_bond_0': Config(
            (
                AttachData(networks[VM_NET_NAME], ETH1),
                AttachData(networks[VLAN_10_NET_NAME], ETH1),
                AttachData(networks[VLAN_20_NET_NAME], BOND0),
                AttachData(networks[VLAN_30_NET_NAME], BOND0),
            ),
            (BondingData(BOND0, [ETH2, ETH3]),),
        ),
        'networks_and_bond_1': Config(
            (
                AttachData(networks[VLAN_30_NET_NAME], ETH2),
                AttachData(networks[VM_NET_NAME], BOND0),
                AttachData(networks[VLAN_10_NET_NAME], BOND0),
                AttachData(networks[VLAN_30_NET_NAME_1], BOND0),
            ),
            (BondingData(BOND0, [ETH1, ETH3]),),
        ),
    }


@pytest.fixture(scope='module')
def networks(system, default_data_center, default_cluster):
    vm_net_ctx = clusterlib.new_assigned_network(VM_NET_NAME, default_data_center, default_cluster)

    vm_vlan_10_net_ctx = clusterlib.new_assigned_network(
        VLAN_10_NET_NAME, default_data_center, default_cluster, vlan=10
    )

    vm_vlan_20_net_ctx = clusterlib.new_assigned_network(
        VLAN_20_NET_NAME, default_data_center, default_cluster, vlan=20
    )

    vm_vlan_30_net_ctx = clusterlib.new_assigned_network(
        VLAN_30_NET_NAME, default_data_center, default_cluster, vlan=30
    )

    vm_vlan_30_net_1_ctx = clusterlib.new_assigned_network(
        VLAN_30_NET_NAME_1, default_data_center, default_cluster, vlan=30
    )

    joblib.AllJobs(system).wait_for_done()
    with (
        vm_net_ctx as vm_network,
        vm_vlan_10_net_ctx as vm_vlan_10_network,
        vm_vlan_20_net_ctx as vm_vlan_20_network,
        vm_vlan_30_net_ctx as vm_vlan_30_network,
        vm_vlan_30_net_1_ctx as vm_vlan_30_network_1,
    ):
        yield {
            VM_NET_NAME: vm_network,
            VLAN_10_NET_NAME: vm_vlan_10_network,
            VLAN_20_NET_NAME: vm_vlan_20_network,
            VLAN_30_NET_NAME: vm_vlan_30_network,
            VLAN_30_NET_NAME_1: vm_vlan_30_network_1,
        }


class CopyHostComparator(object):
    """
    nic0: source nic
    nic1: destination nic
    """

    @staticmethod
    def compare(nic0, nic1):
        return (CopyHostComparator._neither_has_network_attached(nic0, nic1)) or (
            nic0.is_same_network_attachment(nic1)
            and CopyHostComparator._network_attachment_correctly_copied(nic0, nic1)
        )

    @staticmethod
    def _neither_has_network_attached(nic0, nic1):
        return not nic0.is_network_attached() and nic1.is_same_network_attachment(nic0)

    @staticmethod
    def _network_attachment_correctly_copied(nic0, nic1):
        return (
            CopyHostComparator._non_static_ipv4_copied(nic0, nic1)
            or CopyHostComparator._ipv4_static_protocol_disabled(nic0, nic1)
        ) and (
            CopyHostComparator._non_static_ipv6_copied(nic0, nic1)
            or CopyHostComparator._ipv6_static_protocol_disabled(nic0, nic1)
        )

    @staticmethod
    def _non_static_ipv4_copied(nic0, nic1):
        return not nic0.is_static_ipv4() and nic0.boot_protocol_equals(nic1)

    @staticmethod
    def _ipv4_static_protocol_disabled(nic0, nic1):
        """
        Copying network configurations that contain static IPs is not possible.
        In such cases the resulting boot protocol should be disabled.
        """
        return nic0.is_static_ipv4() and nic1.is_disabled_ipv4()

    @staticmethod
    def _non_static_ipv6_copied(nic0, nic1):
        return not nic0.is_static_ipv6() and nic0.ipv6_boot_protocol_equals(nic1)

    @staticmethod
    def _ipv6_static_protocol_disabled(nic0, nic1):
        """
        Copying network configurations that contain static IPs is not possible.
        In such cases the resulting boot protocol should be disabled.
        """
        return nic0.is_static_ipv6() and nic1.is_disabled_ipv6()


@contextlib.contextmanager
def _setup_destination_host(host, attach_data, bonding_data):
    """
    After copy_host_network, the configuration of destination will be different
    than what we originally set up. We therefore have to clean it completely
    to avoid any leftovers.
    """
    host.setup_networks(attach_data, bonding_data=bonding_data)
    try:
        yield
    finally:
        host.clean_all_networking()
