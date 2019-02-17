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
import pytest

import contextlib

from ovirtsdk4 import types

from ovirtlib import clusterlib
from ovirtlib import hostlib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import templatelib
from ovirtlib import virtlib

DEFAULT_NAME = 'Default'
ETH2 = 'eth2'
HOST_QOS = 'host_qos'
VM_QOS = 'vm_qos'
QOS_NAMES = (HOST_QOS, VM_QOS)
QOS_NET = 'qos-net'
QOS_NET_IPv4_ADDR = '192.168.123.3'
QOS_NET_IPv4_MASK = '255.255.255.0'
QOS_VP = 'qos_vp'
NIC2 = 'nic2'
VM0 = 'vm_for_test_qos_config'
DISK0 = 'disk0'
MAX_PEAK_RATE = 34359
MAX_AVG_RATE = MAX_PEAK_RATE / 2
MAX_BURST = 99
MAX_LINKSHARE = 100


@pytest.fixture(scope='module')
def host_qos(default_data_center):
    _host_qos = netlib.QoS(default_data_center)
    # values are in Mbit/sec
    _host_qos.create(name=HOST_QOS,
                     qos_type=types.QosType.HOSTNETWORK,
                     outbound_average_upperlimit=MAX_AVG_RATE,
                     outbound_average_realtime=MAX_AVG_RATE,
                     outbound_average_linkshare=MAX_LINKSHARE)
    yield _host_qos
    default_data_center.remove_qos((HOST_QOS,))


@pytest.fixture(scope='module')
def vm_qos(default_data_center):
    _vm_qos = netlib.QoS(default_data_center)
    # values are in Mbit/sec
    _vm_qos.create(name=VM_QOS,
                   qos_type=types.QosType.NETWORK,
                   inbound_average=MAX_AVG_RATE,
                   inbound_peak=MAX_PEAK_RATE,
                   inbound_burst=MAX_BURST,
                   outbound_average=MAX_AVG_RATE,
                   outbound_peak=MAX_PEAK_RATE,
                   outbound_burst=MAX_BURST)

    yield _vm_qos
    default_data_center.remove_qos((VM_QOS,))


@pytest.fixture(scope='module')
def qos_net(default_data_center, host_qos):
    network = netlib.Network(default_data_center)
    network.create(name=QOS_NET,
                   qos=host_qos,
                   auto_generate_profile=False)
    yield network
    network.remove()


@pytest.fixture(scope='module')
def cluster_net(default_cluster, qos_net):
    cluster_network = clusterlib.ClusterNetwork(default_cluster)
    cluster_network.assign(qos_net, required=False)
    yield cluster_network
    cluster_network.remove()


@pytest.fixture(scope='module')
def cluster_host_up(system, default_cluster):
    any_host_id = default_cluster.host_ids()[0]
    host = hostlib.Host(system)
    host.import_by_id(any_host_id)
    host.wait_for_up_status(timeout=hostlib.HOST_TIMEOUT_LONG)
    yield host


@contextlib.contextmanager
def vm_down(system, default_cluster, default_storage_domain):
    with virtlib.vm_pool(system, size=1) as (vm,):
        vm.create(vm_name=VM0,
                  cluster=default_cluster,
                  template=templatelib.TEMPLATE_BLANK)
        disk = default_storage_domain.create_disk(DISK0)
        disk_att_id = vm.attach_disk(disk=disk)
        vm.wait_for_disk_up_status(disk, disk_att_id)
        vm.wait_for_down_status()
        yield vm


# a. assert QoS configuration on engine was successful
# b. test host QoS: setup_networks on host succeeds with legal QoS values
# c. test VM QoS: the VM manages to power up with legal QoS values
#
def test_setup_net_with_qos(system, default_data_center, default_cluster,
                            default_storage_domain, cluster_host_up,
                            cluster_net, qos_net, vm_qos):

    qos_configs = default_data_center.list_qos()
    assert len([qos for qos in qos_configs if qos.name in QOS_NAMES]) == 2

    attach_data = _create_net_attachment_data(qos_net)
    with hostlib.setup_networks(cluster_host_up, (attach_data,)):
        with netlib.create_vnic_profile(
                system, QOS_VP, qos_net, vm_qos) as profile:
            with vm_down(
                    system, default_cluster, default_storage_domain) as vm:
                vm.create_vnic(NIC2, profile)
                vm.run()
                vm.wait_for_powering_up_status()


def _create_net_attachment_data(qos_net):
    ip_config = netattachlib.create_static_ip_config_assignment(
        addr=QOS_NET_IPv4_ADDR, mask=QOS_NET_IPv4_MASK
    )
    att_data = netattachlib.NetworkAttachmentData(qos_net, ETH2, (ip_config,))
    return att_data
