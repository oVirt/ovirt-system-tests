# -*- coding: utf-8 -*-
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
from __future__ import absolute_import

from lago import utils
from netaddr.ip import IPAddress
from ost_utils import backend
from ost_utils.pytest.fixtures.ansible import ansible_host0
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.network import bonding_network_name
from ost_utils.pytest.fixtures.network import management_network_name
from ovirtsdk4.types import Bonding, HostNic, Option, VnicProfile, VnicPassThrough, VnicPassThroughMode

import test_utils
from test_utils import network_utils_v4
from test_utils import versioning


# DC/Cluster
DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

# Networks
VM_NETWORK = u'VM Network with a very long name and עברית'
VM_NETWORK_IPv4_ADDR = '192.0.2.{}'
VM_NETWORK_IPv4_MASK = '255.255.255.0'
VM_NETWORK_IPv6_ADDR = '2001:0db8:85a3:0000:0000:8a2e:0370:733{}'
VM_NETWORK_IPv6_MASK = '64'
VM_NETWORK_VLAN_ID = 100

MIGRATION_NETWORK = 'Migration_Net'  # MTU 9000

if versioning.cluster_version_ok(4, 3):
    BOND_NAME = 'bond_fancy0'
else:
    BOND_NAME = 'bond0'

MIGRATION_NETWORK_IPv4_ADDR = '192.0.3.{}'
MIGRATION_NETWORK_IPv4_MASK = '255.255.255.0'
MIGRATION_NETWORK_IPv6_ADDR = '1001:0db8:85a3:0000:0000:574c:14ea:0a0{}'
MIGRATION_NETWORK_IPv6_MASK = '64'


def _host_is_attached_to_network(engine, host, network_name, nic_name=None):
    try:
        attachment = network_utils_v4.get_network_attachment(
            engine, host, network_name, DC_NAME)
    except StopIteration:  # there is no attachment of the network to the host
        return False

    if nic_name:
        host_nic = next(nic for nic in host.nics_service().list()
                        if nic.id == attachment.host_nic.id)
        assert nic_name == host_nic.name
    return attachment


def _attach_vm_network_to_host_static_config(api, network_name, host_num):
    engine = api.system_service()

    host = test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME)[host_num]
    host_service = engine.hosts_service().host_service(id=host.id)

    nic_name = backend.ifaces_for(host.name, network_name)[0]  # eth0
    ip_configuration = network_utils_v4.create_static_ip_configuration(
        VM_NETWORK_IPv4_ADDR.format(host_num+1),
        VM_NETWORK_IPv4_MASK,
        VM_NETWORK_IPv6_ADDR.format(host_num+1),
        VM_NETWORK_IPv6_MASK)

    network_utils_v4.attach_network_to_host(
        host_service,
        nic_name,
        VM_NETWORK,
        ip_configuration)

    host_nic = next(nic for nic in host_service.nics_service().list() if
                    nic.name == '{}.{}'.format(nic_name, VM_NETWORK_VLAN_ID))

    assert IPAddress(host_nic.ip.address) == \
        IPAddress(VM_NETWORK_IPv4_ADDR.format(host_num+1))

    assert IPAddress(host_nic.ipv6.address) == \
         IPAddress(VM_NETWORK_IPv6_ADDR.format(host_num+1))


def test_attach_vm_network_to_host_0_static_config(engine_api,
                                                   management_network_name):
    _attach_vm_network_to_host_static_config(engine_api, management_network_name,
                                             host_num=0)


def test_modify_host_0_ip_to_dhcp(engine_api):
    engine = engine_api.system_service()

    host = test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME)[0]
    host_service = engine.hosts_service().host_service(id=host.id)
    ip_configuration = network_utils_v4.create_dhcp_ip_configuration()

    network_utils_v4.modify_ip_config(engine, host_service, VM_NETWORK,
                                      ip_configuration)

    # TODO: once the VLANs/dnsmasq issue is resolved,
    # (https://github.com/lago-project/lago/issues/375)
    # verify ip configuration.


def test_detach_vm_network_from_host_0(engine_api):
    engine = engine_api.system_service()

    host = test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME)[0]
    host_service = engine.hosts_service().host_service(id=host.id)

    network_utils_v4.set_network_required_in_cluster(
        engine, VM_NETWORK, CLUSTER_NAME, False)
    network_utils_v4.detach_network_from_host(engine, host_service, VM_NETWORK)

    assert not _host_is_attached_to_network(engine, host_service, VM_NETWORK)


def test_bond_nics(engine_api, bonding_network_name):
    engine = engine_api.system_service()

    def _bond_nics(number, host):
        slaves = [
            HostNic(name=nic)
            for nic in backend.ifaces_for(host.name, bonding_network_name)
        ]

        options = [
            Option(name='mode', value='active-backup'),
            Option(name='miimon', value='200'),
            ]

        bond = HostNic(
            name=BOND_NAME,
            bonding=Bonding(slaves=slaves, options=options))

        ip_configuration = network_utils_v4.create_static_ip_configuration(
            MIGRATION_NETWORK_IPv4_ADDR.format(number),
            MIGRATION_NETWORK_IPv4_MASK,
            MIGRATION_NETWORK_IPv6_ADDR.format(number),
            MIGRATION_NETWORK_IPv6_MASK)

        host_service = engine.hosts_service().host_service(id=host.id)
        network_utils_v4.attach_network_to_host(
            host_service, BOND_NAME, MIGRATION_NETWORK, ip_configuration,
            [bond])

    hosts = test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME)
    utils.invoke_in_parallel(_bond_nics, list(range(1, len(hosts) + 1)), hosts)

    for host in test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME):
        host_service = engine.hosts_service().host_service(id=host.id)
        assert _host_is_attached_to_network(
            engine, host_service, MIGRATION_NETWORK, nic_name=BOND_NAME)


def test_verify_interhost_connectivity_ipv4(ansible_host0):
    ansible_host0.shell(
        'ping -c 1 {}'.format(MIGRATION_NETWORK_IPv4_ADDR.format(2))
    )


def test_verify_interhost_connectivity_ipv6(ansible_host0):
    ansible_host0.shell(
        'ping -c 1 -6 {}'.format(MIGRATION_NETWORK_IPv6_ADDR.format(2))
    )


def test_remove_bonding(engine_api):
    engine = engine_api.system_service()

    def _remove_bonding(host):
        host_service = engine.hosts_service().host_service(id=host.id)
        network_utils_v4.detach_network_from_host(
            engine, host_service, MIGRATION_NETWORK, BOND_NAME)

    network_utils_v4.set_network_required_in_cluster(engine, MIGRATION_NETWORK,
                                                     CLUSTER_NAME, False)
    utils.invoke_in_parallel(
        _remove_bonding, test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME))

    for host in test_utils.hosts_in_cluster_v4(engine, CLUSTER_NAME):
        host_service = engine.hosts_service().host_service(id=host.id)
        assert not _host_is_attached_to_network(engine, host_service,
                                                MIGRATION_NETWORK)


def test_attach_vm_network_to_both_hosts_static_config(engine_api,
                                                       management_network_name):
    # preparation for 004 and 006
    for host_num in (0, 1):
        _attach_vm_network_to_host_static_config(engine_api,
                                                 management_network_name,
                                                 host_num)
