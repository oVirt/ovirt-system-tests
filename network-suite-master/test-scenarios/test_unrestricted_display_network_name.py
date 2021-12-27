#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
import pytest

from fixtures.host import ETH1

from ovirtlib import clusterlib
from ovirtlib import joblib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import templatelib
from ovirtlib import virtlib


@pytest.fixture(scope='module')
def display_network(host_0, default_data_center, default_cluster):
    DISPLAY_NET = 'רשת עם שם ארוך מאוד'

    network = netlib.Network(default_data_center)
    network.create(name=DISPLAY_NET)
    try:
        cluster_network = clusterlib.ClusterNetwork(default_cluster)
        cluster_network.assign(network)
        cluster_network.set_usages([netlib.NetworkUsage.DISPLAY])
        yield network
    finally:
        network.remove()


@pytest.fixture(scope='module')
def display_network_vnic_profile(system, display_network):
    vnic_profile = display_network.vnic_profile()
    yield vnic_profile
    vnic_profile.remove()


@pytest.fixture(scope='module')
def display_network_attached_to_host_0(host_0_up, display_network, af):
    ip_assign = {
        'inet': netattachlib.StaticIpv4Assignment('192.0.3.1', '255.255.255.0'),
        'inet6': netattachlib.StaticIpv6Assignment('fd8f:192:0:3::1', '64'),
    }
    disp_att_data = netattachlib.NetworkAttachmentData(display_network, ETH1, (ip_assign[af.family],))
    host_0_up.setup_networks([disp_att_data])
    yield host_0_up
    host_0_up.remove_networks([display_network])


@pytest.fixture(scope='module')
def vm_0_with_display_network_and_disk(
    system,
    default_cluster,
    default_storage_domain,
    display_network_vnic_profile,
):
    VM_0 = 'test_unrestricted_display_network_name_vm_0'
    VNIC_1 = 'vnic1'

    with virtlib.vm_pool(system, size=1) as (vm_0,):
        vm_0.create(
            vm_name=VM_0,
            cluster=default_cluster,
            template=templatelib.TEMPLATE_BLANK,
        )
        disk_0 = default_storage_domain.create_disk('disk0')
        vm_0.attach_disk(disk=disk_0)
        vm_0.wait_for_down_status()
        vm_0.create_vnic(VNIC_1, display_network_vnic_profile)
        vm_0.wait_for_down_status()
        yield vm_0


@pytest.mark.usefixtures('host_1_up', 'display_network_attached_to_host_0')
def test_run_vm_with_unrestricted_display_network_name(system, vm_0_with_display_network_and_disk):
    vm_0_with_display_network_and_disk.run()
    vm_0_with_display_network_and_disk.wait_for_up_status()
    joblib.AllJobs(system).wait_for_done()
    vm_0_with_display_network_and_disk.stop()
    vm_0_with_display_network_and_disk.wait_for_down_status()
