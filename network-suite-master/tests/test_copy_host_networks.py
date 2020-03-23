#
# Copyright 2020 Red Hat, Inc.
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
from ovirtlib import hostlib
from ovirtlib import netattachlib

from testlib import suite

ETH1 = 'eth1'
ETH2 = 'eth2'

VM_NET_NAME = 'vm-net'
VLAN_10_NET_NAME = 'vlan-10-net'


@suite.skip_suites_below('4.4')
@suite.skip_sdk_below('4.4')
def test_copy_host_networks(configured_hosts):
    source_host = configured_hosts[0]
    destination_host = configured_hosts[1]

    destination_host.copy_networks_from(source_host)
    assert source_host.compare_nics_except_mgmt(
        destination_host, CopyHostComparator.compare
    )


@pytest.fixture(
    scope='function',
    params=[('ovirtmgmt_only', 'ovirtmgmt_only'),
            ('vlan_and_nonvlan', 'single_network')],
    ids=['copy_nothing_to_host_with_nothing',
         'copy_vlan_and_nonvlan_to_host_with_single_network'],
)
def configured_hosts(request, host_attachments, host_0_up, host_1_up):
    source_attach_data = host_attachments[request.param[0]]
    destination_attach_data = host_attachments[request.param[1]]

    setup_host0 = hostlib.setup_networks(host_0_up, source_attach_data)
    setup_host1 = hostlib.setup_networks(host_1_up, destination_attach_data)
    with setup_host0, setup_host1:
        yield (host_0_up, host_1_up)

    host_1_up.clean_networks()


@pytest.fixture(scope='module')
def host_attachments(networks):
    return {
        'ovirtmgmt_only': [],
        'single_network': [
            netattachlib.NetworkAttachmentData(networks[VM_NET_NAME], ETH1)
        ],
        'vlan_and_nonvlan': [
            netattachlib.NetworkAttachmentData(
                networks[VLAN_10_NET_NAME], ETH1),
            netattachlib.NetworkAttachmentData(networks[VM_NET_NAME], ETH2),
        ],
    }


@pytest.fixture(scope='module')
def networks(default_data_center, default_cluster):
    vm_net_ctx = clusterlib.new_assigned_network(
        VM_NET_NAME, default_data_center, default_cluster)

    vm_vlan_10_net_ctx = clusterlib.new_assigned_network(
        VLAN_10_NET_NAME, default_data_center, default_cluster, vlan=10)

    with vm_net_ctx as vm_network, vm_vlan_10_net_ctx as vm_vlan_10_network:
        yield {
            VM_NET_NAME: vm_network,
            VLAN_10_NET_NAME: vm_vlan_10_network,
        }


class CopyHostComparator(object):
    """
    nic0: source nic
    nic1: destination nic
    """

    @staticmethod
    def compare(nic0, nic1):
        return (
            CopyHostComparator._neither_has_network_attached(nic0, nic1)
        ) or (
            nic0.is_same_network_attachment(nic1)
            and CopyHostComparator._network_attachment_correctly_copied(
                nic0, nic1)
        )

    @staticmethod
    def _neither_has_network_attached(nic0, nic1):
        return (
            not nic0.is_network_attached()
            and nic1.is_same_network_attachment(nic0)
        )

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
        return (
            not nic0.is_static_ipv6()
            and nic0.ipv6_boot_protocol_equals(nic1)
        )

    @staticmethod
    def _ipv6_static_protocol_disabled(nic0, nic1):
        """
        Copying network configurations that contain static IPs is not possible.
        In such cases the resulting boot protocol should be disabled.
        """
        return nic0.is_static_ipv6() and nic1.is_disabled_ipv6()
