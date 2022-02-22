#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from contextlib import contextmanager

import pytest

from ovirtlib import clusterlib
from ovirtlib import joblib
from ovirtlib import netlib
from ovirtlib import virtlib
from testlib import suite


VNIC0_NAME = 'nic001'
VM0_NAME = 'test_ovn_provider_integration_with_ovirt_vm_0'
VNIC0_MAC = '00:1a:4a:17:15:50'


@pytest.fixture(scope='module')
def running_vm_0(
    ovirt_external_network,
    system,
    default_cluster,
    default_storage_domain,
    cirros_template,
):
    cluster_network = clusterlib.ClusterNetwork(default_cluster)
    cluster_network.assign(ovirt_external_network)
    with virtlib.vm_pool(system, size=1) as (vm_0,):
        vm_0.create(vm_name=VM0_NAME, cluster=default_cluster, template=cirros_template)

        vnic_profile0 = ovirt_external_network.vnic_profile()

        vm0_vnic_0 = netlib.Vnic(vm_0)
        vm0_vnic_0.create(name=VNIC0_NAME, vnic_profile=vnic_profile0, mac_addr=VNIC0_MAC)

        vm_0.wait_for_down_status()
        vm_0.run()
        vm_0.wait_for_up_status()
        joblib.AllJobs(system).wait_for_done()
        yield vm_0


def test_connect_vm_to_external_network(running_vm_0, default_ovn_provider_client):
    vm0_vnic_0 = running_vm_0.get_vnic(VNIC0_NAME)

    assert not vm0_vnic_0.vnic_profile.filter

    ovn_port = _lookup_port_by_device_id(vm0_vnic_0.id, default_ovn_provider_client)
    assert ovn_port
    assert vm0_vnic_0.mac_address == ovn_port.mac_address


@suite.skip_suites_below('4.3')
def test_modify_vnic_sec_groups_on_ext_networks(
    running_vm_0, system, ovirt_external_network, default_ovn_provider_client
):
    with netlib.create_vnic_profile(system, 'temporary', ovirt_external_network) as profile:
        with _create_security_group(default_ovn_provider_client, 'temporary', 'temporary sec group') as sec_group:
            profile.custom_properties = [netlib.CustomProperty('SecurityGroups', sec_group.id)]
            profile.filter = None

            vnic = running_vm_0.get_vnic(VNIC0_NAME)
            def_group = default_ovn_provider_client.get_security_group('Default')
            vnic.vnic_profile.custom_properties = [netlib.CustomProperty('SecurityGroups', def_group.id)]

            with vnic.toggle_profile(profile):
                assert vnic.vnic_profile.name == 'temporary'
                assert [sec_group.id] == [p.value for p in vnic.vnic_profile.custom_properties]

                ovn_port = _lookup_port_by_device_id(vnic.id, default_ovn_provider_client)
                assert ovn_port
                assert [sec_group.id] == ovn_port.security_group_ids


def _lookup_port_by_device_id(vnic_id, default_ovn_provider_cloud):
    for port in default_ovn_provider_cloud.list_ports():
        device_id = port.get('device_id')
        if device_id and device_id == vnic_id:
            return port
    return None


@contextmanager
def _create_security_group(ovn_provider_client, name, description):
    security_group = ovn_provider_client.create_security_group(name, description)
    try:
        yield security_group
    finally:
        ovn_provider_client.delete_security_group(security_group.id)
