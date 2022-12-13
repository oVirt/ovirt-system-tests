#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

from contextlib import contextmanager
import os
import time

import pytest

from ovirtlib import clusterlib
from ovirtlib import joblib
from ovirtlib import netlib
from ovirtlib import sdkentity
from ovirtlib import syncutil
from ovirtlib import sshlib
from ovirtlib import virtlib
from ovirtlib.ansiblelib import Playbook
from testlib import suite


MTU = 1500
VNIC0_NAME = 'vnic0'
VNIC_INTERNAL = 'vnic-internal'
VM0_NAME = 'test_ovn_physnet_vm_0'
OVN_PHYSNET_NAME = 'ovn_ovirtmgmt'
EXTERNAL_NETWORK = r'.*Only an external network may be attached to VM in a cluster with OVS switch type'


@pytest.fixture(scope='module')
def ovn_physnet_small_mtu(
    default_data_center,
    ovirtmgmt_network,
    ovs_cluster,
    default_ovn_provider,
    default_ovn_provider_client,
):
    """
    To remove an external logical network, the network has to be removed
    directly on its provider by OpenStack Networking API.
    The entity representing the external network inside oVirt engine
    has to be removed explicitly here, because auto_sync is disabled for the
    provider.
    """
    network = netlib.Network(default_data_center)
    network.create(
        OVN_PHYSNET_NAME,
        external_provider=default_ovn_provider,
        external_provider_physical_network=ovirtmgmt_network,
        mtu=MTU,
    )
    try:
        cluster_network = clusterlib.ClusterNetwork(ovs_cluster)
        cluster_network.assign(network)
        provider_network = _get_network_by_name(default_ovn_provider_client, OVN_PHYSNET_NAME)
        _update_network_security(default_ovn_provider_client, provider_network.id, ovirtmgmt_network.name, False)
        yield network
    finally:
        network.remove()
        default_ovn_provider_client.delete_network(OVN_PHYSNET_NAME)


@pytest.fixture(scope='module')
def vm_in_ovs_cluster_down(
    system,
    ovs_cluster,
    host_in_ovs_cluster,
    default_storage_domain,
    cirros_template,
):
    with virtlib.vm_pool(system, size=1) as (vm,):
        vm.create(vm_name=VM0_NAME, cluster=ovs_cluster, template=cirros_template)
        vm.wait_for_down_status()
        yield vm


@pytest.fixture(scope='module')
def vnic_attached_to_ovn_network(system, vm_in_ovs_cluster_down, ovn_physnet_small_mtu):
    vnic_profile = ovn_physnet_small_mtu.vnic_profile()
    vm_vnic = netlib.Vnic(vm_in_ovs_cluster_down)
    vm_vnic.create(name=VNIC0_NAME, vnic_profile=vnic_profile)
    return vm_vnic


@pytest.fixture(scope='module')
def vm_in_ovn_network_up(
    system, vm_in_ovs_cluster_down, cirros_serial_console, vnic_attached_to_ovn_network, target, af
):
    vm_in_ovs_cluster_down.run_once(cloud_init_hostname=VM0_NAME)
    vm_in_ovs_cluster_down.wait_for_up_status()
    joblib.AllJobs(system).wait_for_done()
    if af.is6:
        cirros_serial_console.add_static_ip(vm_in_ovs_cluster_down.id, f'{target}/64', 'eth0')
    yield vm_in_ovs_cluster_down


@pytest.fixture(scope='module')
def ssh_host_not_in_ovs_cluster(host_not_in_ovs_cluster):
    return sshlib.Node(host_not_in_ovs_cluster.address, host_not_in_ovs_cluster.root_password)


@pytest.fixture(scope='module')
def host_not_in_ovs_cluster(host_in_ovs_cluster, host_0, host_1):
    return next(candidate for candidate in [host_0, host_1] if candidate.id != host_in_ovs_cluster.id)


@pytest.fixture(scope='module')
def target(host_in_ovs_cluster, af):
    if af.is6:
        return f'fd8f:1391:3a82:' f'{host_in_ovs_cluster.address.split(":")[3]}' f'::cafe:cafe'
    else:
        return VM0_NAME


def test_vnic_cannot_connect_physical_network(vm_in_ovs_cluster_down, ovirtmgmt_vnic_profile):
    vnic = netlib.Vnic(vm_in_ovs_cluster_down)
    with pytest.raises(sdkentity.EntityCreationError, match=EXTERNAL_NETWORK):
        vnic.create(name=VNIC_INTERNAL, vnic_profile=ovirtmgmt_vnic_profile)


@suite.xfail_suite_43('BZ 1817589')
def test_connect_vm_to_external_physnet(
    system, ovs_cluster, ssh_host_not_in_ovs_cluster, vm_in_ovn_network_up, target, af
):
    syncutil.sync(
        exec_func=ssh_host_not_in_ovs_cluster.ping_successful,
        exec_func_args=(target, af.version, _max_icmp_data_size(af.family)),
        success_criteria=lambda success: success,
    )


@suite.xfail_suite_43('BZ 1817589')
def test_max_mtu_size(
    system,
    ovs_cluster,
    ssh_host_not_in_ovs_cluster,
    ovn_physnet_small_mtu,
    vm_in_ovn_network_up,
    target,
    af,
):
    syncutil.sync(
        exec_func=ssh_host_not_in_ovs_cluster.ping_successful,
        exec_func_args=(target, af.version, _max_icmp_data_size(af.family)),
        success_criteria=lambda success: success,
    )


@suite.xfail_suite_43('BZ 1817589')
def test_over_max_mtu_size(
    system, ovs_cluster, ssh_host_not_in_ovs_cluster, ovn_physnet_small_mtu, vm_in_ovn_network_up, target, af
):
    ssh_host_not_in_ovs_cluster.assert_no_ping(target, af.version, _max_icmp_data_size(af.family) + 1)


@suite.skip_suites_below('4.3')
@suite.xfail_suite_43('BZ 1817589')
def test_security_groups_allow_icmp(
    system,
    ovs_cluster,
    host_not_in_ovs_cluster,
    ssh_host_not_in_ovs_cluster,
    default_ovn_provider_client,
    ovn_physnet_small_mtu,
    vm_in_ovn_network_up,
    vnic_attached_to_ovn_network,
    target,
    af,
    ansible_private_dir,
):
    syncutil.sync(
        exec_func=ssh_host_not_in_ovs_cluster.ping_successful,
        exec_func_args=(target, af.version, _max_icmp_data_size(af.family)),
        success_criteria=lambda success: success,
    )

    with _enable_port_security(vnic_attached_to_ovn_network, default_ovn_provider_client):
        time.sleep(10)
        ssh_host_not_in_ovs_cluster.assert_no_ping(target, af.version, _max_icmp_data_size(af.family))

        with _allow_icmp_from_host(host_not_in_ovs_cluster, af.version, ansible_private_dir):
            syncutil.sync(
                exec_func=ssh_host_not_in_ovs_cluster.ping_successful,
                exec_func_args=(target, af.version, _max_icmp_data_size(af.family)),
                success_criteria=lambda success: success,
            )


@contextmanager
def _enable_port_security(vnic, ovn_provider):
    ovn_port = _lookup_port_by_device_id(vnic.id, ovn_provider)
    ovn_provider.update_port(ovn_port.id, port_security_enabled=True)
    try:
        yield
    finally:
        ovn_provider.update_port(ovn_port.id, port_security_enabled=False)


def _lookup_port_by_device_id(vnic_id, default_ovn_provider_cloud):
    for port in default_ovn_provider_cloud.list_ports():
        device_id = port.get('device_id')
        if device_id and device_id == vnic_id:
            return port
    return None


@contextmanager
def _allow_icmp_from_host(host, ip_version, private_dir):
    _provision_icmp_rule(host.address, ip_version, action='apply', private_dir=private_dir)
    try:
        yield
    finally:
        _forbid_icmp_from_host(host, ip_version, private_dir)


def _forbid_icmp_from_host(host, ip_version, private_dir):
    _provision_icmp_rule(host.address, ip_version, action='remove', private_dir=private_dir)


def _provision_icmp_rule(source_ip, ip_version, action, private_dir):
    playbook_path = os.path.join(suite.playbook_dir(), action + '_icmp_rule_on_default_sec_group.yml')
    playbook = Playbook(
        playbook_path,
        extra_vars={
            'source_ip': source_ip,
            'cloud_name': 'ovirt',
            'ether_type': f'IPv{ip_version}',
        },
        private_dir=private_dir,
    )
    playbook.run()


def _get_network_by_name(ovn_provider, network_name):
    return ovn_provider.get_network(network_name)


def _max_icmp_data_size(address_family):
    icmp_header_size = 8
    ip_header_size = {'inet': 20, 'inet6': 40}
    return MTU - icmp_header_size - ip_header_size[address_family]


def _update_network_security(ovn_provider, ovn_net_id, physical_network, enabled):
    # openstacksdk does diff for every update, it works as follows:
    # 1) User request update
    # 2) openstacksdk gets the entity that is configured on ovirt-provider-ovn
    # 3) openstacksdk makes diff of the update and the entity
    # 4) openstacksdk sends the diff as update
    # This unfortunately causes the "provider" to be lost when we send it in single update.
    # As the "provider" is already configured the diff will contain only "port_security_enabled",
    # empty "provider" means that ovirt-provider-ovn removes this attribute.
    # To get it back we need to send second update with the "provider" being specified again.
    # As for "why" is the "provider" removed when it is empty, it is design choice of ovirt-provider-ovn,
    # it is the only parameter that gets removed when empty on network update.
    # https://github.com/oVirt/ovirt-provider-ovn/blob/1.2.35/provider/neutron/neutron_api.py#L258
    ovn_provider.update_network(
        ovn_net_id,
        port_security_enabled=enabled,
    )
    ovn_provider.update_network(
        ovn_net_id,
        provider={'physical_network': physical_network, 'network_type': 'flat'},
    )
