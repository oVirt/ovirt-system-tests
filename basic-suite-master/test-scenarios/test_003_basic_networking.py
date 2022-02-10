#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#
from __future__ import absolute_import

import ipaddress
import random

import pytest

from ost_utils import utils

from ost_utils.ovirtlib import clusterlib
from ost_utils.ovirtlib import datacenterlib
from ost_utils.ovirtlib import hostlib
from ost_utils.ovirtlib import netattachlib
from ost_utils.ovirtlib import netlib
from ost_utils.ovirtlib import system as systemlib

# DC/Cluster
DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

# Networks
VM_NETWORK = u'VM Network with a very long name and עברית'
VM_NETWORK_VLAN_ID = 100
MIGRATION_NETWORK = 'Migration_Net'  # MTU 9000
BOND_NAME = 'bond_fancy0'
ETH0 = 'eth0'


def test_attach_vm_network_to_host_0_static_config(host0, vm_network, static_ips):
    static_ip = static_ips['vm_net_0']
    attach_data = netattachlib.NetworkAttachmentData(vm_network, ETH0, (static_ip['inet'], static_ip['inet6']))
    host0.setup_networks((attach_data,))
    host_nic = hostlib.HostNic(host0)
    host_nic.import_by_name(f'{ETH0}.{VM_NETWORK_VLAN_ID}')
    _assert_expected_ips(host_nic, static_ip)


def test_modify_host_0_ip_to_dhcp(host0, vm_network):
    attach_data = netattachlib.NetworkAttachmentData(
        vm_network, ETH0, (netattachlib.IPV4_DHCP, netattachlib.IPV6_POLY_DHCP_AUTOCONF)
    )
    host0.setup_networks((attach_data,))

    # TODO: once the VLANs/dnsmasq issue is resolved,
    # (https://github.com/lago-project/lago/issues/375)
    # verify ip configuration.


def test_detach_vm_network_from_host(host0, vm_network, vm_cluster_network):
    vm_cluster_network.update(required=False)
    host0.remove_networks((vm_network,))
    assert not host0.are_networks_attached((vm_network,))


def test_bond_nics(host0, host1, migration_network, bonding_data, bond_attachment_data):
    for i, host in enumerate((host0, host1)):
        host.setup_networks(attachments_data=(bond_attachment_data[i],), bonding_data=(bonding_data[i],))
        attachment_data = host.get_attachment_data_for_networks((migration_network,))
        assert attachment_data
        bond = hostlib.Bond(host)
        bond.import_by_id(next(iter(attachment_data)).nic_id)
        assert bond.name == BOND_NAME


def test_verify_interhost_connectivity_ipv4(ansible_host0, static_ips):
    host_1_ip_addr = static_ips['migration_net_1']['inet'].address
    ansible_host0.shell('ping -c 1 {}'.format(host_1_ip_addr))


def test_verify_interhost_connectivity_ipv6(ansible_host0, static_ips):
    host_1_ip_addr = static_ips['migration_net_1']['inet6'].address
    ansible_host0.shell('ping -c 1 -6 {}'.format(host_1_ip_addr))


def test_remove_bonding(host0, host1, migration_network, migration_cluster_network):
    migration_cluster_network.update(required=False)
    for host in host0, host1:
        bond = hostlib.Bond(host)
        bond.import_by_name(BOND_NAME)
        host.remove_attachments(
            removed_attachments_data=host.get_attachment_data_for_networks((migration_network,)),
            removed_bonding_data=(bond.bonding_data,),
        )
        assert not host.are_networks_attached((migration_network,))


def test_attach_vm_network_to_both_hosts_static_config(host0, host1, vm_network, static_ips):
    # preparation for 004 and 006
    for i, host in enumerate((host0, host1)):
        static_ip = static_ips[f'vm_net_{i}']
        attach_data = netattachlib.NetworkAttachmentData(vm_network, ETH0, (static_ip['inet'], static_ip['inet6']))
        host.setup_networks((attach_data,))
        host_nic = hostlib.HostNic(host)
        host_nic.import_by_name(f'{ETH0}.{VM_NETWORK_VLAN_ID}')
        _assert_expected_ips(host_nic, static_ip)


@pytest.fixture(scope='module')
def sdk_system(engine_api):
    sdk_system = systemlib.SDKSystemRoot()
    sdk_system.import_conn(engine_api)
    return sdk_system


@pytest.fixture(scope='module')
def data_center(sdk_system):
    dc = datacenterlib.DataCenter(sdk_system)
    dc.import_by_name(DC_NAME)
    return dc


@pytest.fixture(scope='module')
def test_cluster(sdk_system):
    cl = clusterlib.Cluster(sdk_system)
    cl.import_by_name(CLUSTER_NAME)
    return cl


@pytest.fixture(scope='module')
def host0(sdk_system, host0_hostname):
    host = hostlib.Host(sdk_system)
    host.import_by_name(host0_hostname)
    return host


@pytest.fixture(scope='module')
def host1(sdk_system, host1_hostname):
    host = hostlib.Host(sdk_system)
    host.import_by_name(host1_hostname)
    return host


@pytest.fixture(scope='module')
def vm_network(data_center):
    vm_network = netlib.Network(data_center)
    vm_network.import_by_name(VM_NETWORK)
    return vm_network


@pytest.fixture(scope='module')
def migration_network(data_center):
    migration_network = netlib.Network(data_center)
    migration_network.import_by_name(MIGRATION_NETWORK)
    return migration_network


@pytest.fixture(scope='module')
def vm_cluster_network(test_cluster):
    vm_cluster_network = clusterlib.ClusterNetwork(test_cluster)
    vm_cluster_network.import_by_name(VM_NETWORK)
    return vm_cluster_network


@pytest.fixture(scope='module')
def migration_cluster_network(test_cluster):
    migration_cluster_network = clusterlib.ClusterNetwork(test_cluster)
    migration_cluster_network.import_by_name(MIGRATION_NETWORK)
    return migration_cluster_network


@pytest.fixture(scope='module')
def seed():
    random.seed()
    return random.choice(range(2, 250))


@pytest.fixture(scope='module')
def static_ips(seed):
    return {
        'vm_net_0': _static_ip_assignment(seed, seed),  # vm_network on host_0
        'vm_net_1': _static_ip_assignment(seed, seed + 1),  # vm_network on host_1
        'migration_net_0': _static_ip_assignment(seed + 1, seed),  # migration_network on host_0
        'migration_net_1': _static_ip_assignment(seed + 1, seed + 1),  # migration_network on host_1
    }


@pytest.fixture(scope='module')
def bonding_data(host0, host1, backend, bonding_network_name):
    bonding_data = []
    for host in host0, host1:
        bonded_nic_names = [
            host.get_nic_for_mac_address(mac_address).name
            for mac_address in backend.macs_for(host.name, bonding_network_name)
        ]
        bonding_data.append(netattachlib.ActiveSlaveBonding(BOND_NAME, bonded_nic_names, {'miimon': '200'}))
    return bonding_data


@pytest.fixture(scope='module')
def bond_attachment_data(host0, host1, static_ips, migration_network):
    attachment_data = []
    for i, host in enumerate((host0, host1)):
        static_ip_assignment = static_ips[f'migration_net_{i}']
        attachment_data.append(
            netattachlib.NetworkAttachmentData(
                migration_network, BOND_NAME, (static_ip_assignment['inet'], static_ip_assignment['inet6'])
            )
        )
    return attachment_data


def _static_ip_assignment(net_seed, host_seed):
    return {
        'inet': netattachlib.StaticIpv4Assignment(f'192.0.{net_seed}.{host_seed}', '255.255.255.0'),
        'inet6': netattachlib.StaticIpv6Assignment(f'2001:0db8:85a3:{net_seed}::{host_seed}', '64'),
    }


def _assert_expected_ips(host_nic, static_ips):
    assert ipaddress.ip_address(host_nic.ip4_address) == ipaddress.ip_address(static_ips['inet'].address)
    assert ipaddress.ip_address(host_nic.ip6_address) == ipaddress.ip_address(static_ips['inet6'].address)
