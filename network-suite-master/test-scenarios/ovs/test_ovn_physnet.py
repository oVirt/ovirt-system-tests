#
# Copyright 2018-2021 Red Hat, Inc.
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
from testlib import shade_hack
from testlib import suite


MTU = 1500
VNIC0_NAME = 'vnic0'
VNIC_INTERNAL = 'vnic-internal'
VM0_NAME = 'test_ovn_physnet_vm_0'
OVN_PHYSNET_NAME = 'ovn_ovirtmgmt'
EXTERNAL_NETWORK = r'.*Only an external network may be attached to VM' \
                   r' in a cluster with OVS switch type'


@pytest.fixture(scope='module')
def ovn_physnet_small_mtu(default_data_center, ovirtmgmt_network, ovs_cluster,
                          default_ovn_provider, default_ovn_provider_client):
    """
    To remove an external logical network, the network has to be removed
    directly on its provider by OpenStack Networking API.
    The entity representing the external network inside oVirt engine
    has to be removed explicitly here, because auto_sync is disabled for the
    provider.
    """
    network = netlib.Network(default_data_center)
    network.create(OVN_PHYSNET_NAME,
                   external_provider=default_ovn_provider,
                   external_provider_physical_network=ovirtmgmt_network,
                   mtu=MTU)
    try:
        cluster_network = clusterlib.ClusterNetwork(ovs_cluster)
        cluster_network.assign(network)
        provider_network = _get_network_by_name(default_ovn_provider_client,
                                                OVN_PHYSNET_NAME)
        _disable_network_port_security(ovirtmgmt_network.name,
                                       provider_network.id,
                                       default_ovn_provider_client)
        yield network
    finally:
        network.remove()
        default_ovn_provider_client.delete_network(OVN_PHYSNET_NAME)


@pytest.fixture(scope='module')
def vm_in_ovs_cluster_down(system, ovs_cluster, host_in_ovs_cluster,
                           default_storage_domain, cirros_template):
    with virtlib.vm_pool(system, size=1) as (vm,):
        vm.create(vm_name=VM0_NAME, cluster=ovs_cluster,
                  template=cirros_template)
        vm.wait_for_down_status()
        yield vm


@pytest.fixture(scope='module')
def vnic_attached_to_ovn_network(system, vm_in_ovs_cluster_down,
                                 ovn_physnet_small_mtu):
    vnic_profile = ovn_physnet_small_mtu.vnic_profile()
    vm_vnic = netlib.Vnic(vm_in_ovs_cluster_down)
    vm_vnic.create(name=VNIC0_NAME, vnic_profile=vnic_profile)
    return vm_vnic


@pytest.fixture(scope='module')
def vm_in_ovn_network_up(system, vm_in_ovs_cluster_down, serial_console,
                         vnic_attached_to_ovn_network, target):
    vm_in_ovs_cluster_down.run_once(cloud_init_hostname=VM0_NAME)
    vm_in_ovs_cluster_down.wait_for_up_status()
    joblib.AllJobs(system).wait_for_done()
    if suite.af().is6:
        serial_console.add_static_ip(
            vm_in_ovs_cluster_down.id, f'{target}/64', 'eth0'
        )
    yield vm_in_ovs_cluster_down


@pytest.fixture(scope='module')
def ssh_host_not_in_ovs_cluster(host_not_in_ovs_cluster):
    return sshlib.Node(
        host_not_in_ovs_cluster.address, host_not_in_ovs_cluster.root_password
    )


@pytest.fixture(scope='module')
def host_not_in_ovs_cluster(host_in_ovs_cluster, host_0, host_1):
    return next(candidate for candidate in [host_0, host_1]
                if candidate.id != host_in_ovs_cluster.id)


@pytest.fixture(scope='module')
def target(host_in_ovs_cluster):
    if suite.af().is6:
        return (
            f'fd8f:1391:3a82:'
            f'{host_in_ovs_cluster.address.split(":")[3]}'
            f'::cafe:cafe'
        )
    else:
        return VM0_NAME


@suite.xfail_suite_master('ovn 2.15 upgrade not complete')
def test_vnic_cannot_connect_physical_network(vm_in_ovs_cluster_down,
                                              ovirtmgmt_vnic_profile):
    vnic = netlib.Vnic(vm_in_ovs_cluster_down)
    with pytest.raises(sdkentity.EntityCreationError, match=EXTERNAL_NETWORK):
        vnic.create(name=VNIC_INTERNAL, vnic_profile=ovirtmgmt_vnic_profile)


@suite.xfail_suite_master('ovn 2.15 upgrade not complete')
@suite.xfail_suite_43('BZ 1817589')
def test_connect_vm_to_external_physnet(system, ovs_cluster,
                                        ssh_host_not_in_ovs_cluster,
                                        vm_in_ovn_network_up, target):
    syncutil.sync(exec_func=ssh_host_not_in_ovs_cluster.ping_successful,
                  exec_func_args=(target, _max_icmp_data_size()),
                  success_criteria=lambda success: success)


@suite.xfail_suite_master('ovn 2.15 upgrade not complete')
@suite.xfail_suite_43('BZ 1817589')
def test_max_mtu_size(system, ovs_cluster, ssh_host_not_in_ovs_cluster,
                      ovn_physnet_small_mtu, vm_in_ovn_network_up, target):
    syncutil.sync(exec_func=ssh_host_not_in_ovs_cluster.ping_successful,
                  exec_func_args=(target, _max_icmp_data_size()),
                  success_criteria=lambda success: success)


@suite.xfail_suite_master('ovn 2.15 upgrade not complete')
@suite.xfail_suite_43('BZ 1817589')
def test_over_max_mtu_size(system, ovs_cluster, ssh_host_not_in_ovs_cluster,
                           ovn_physnet_small_mtu, vm_in_ovn_network_up,
                           target):
    ssh_host_not_in_ovs_cluster.assert_no_ping(target,
                                               _max_icmp_data_size() + 1)


@suite.xfail_suite_master('ovn 2.15 upgrade not complete')
@suite.skip_suites_below('4.3')
@suite.xfail_suite_43('BZ 1817589')
def test_security_groups_allow_icmp(system, ovs_cluster,
                                    host_not_in_ovs_cluster,
                                    ssh_host_not_in_ovs_cluster,
                                    default_ovn_provider_client,
                                    ovn_physnet_small_mtu,
                                    vm_in_ovn_network_up,
                                    vnic_attached_to_ovn_network,
                                    target):
    syncutil.sync(exec_func=ssh_host_not_in_ovs_cluster.ping_successful,
                  exec_func_args=(target, _max_icmp_data_size()),
                  success_criteria=lambda success: success)

    with _enable_port_security(vnic_attached_to_ovn_network,
                               default_ovn_provider_client):
        time.sleep(10)
        ssh_host_not_in_ovs_cluster.assert_no_ping(target,
                                                   _max_icmp_data_size())

        with _allow_icmp_from_host(host_not_in_ovs_cluster):
            syncutil.sync(
                exec_func=ssh_host_not_in_ovs_cluster.ping_successful,
                exec_func_args=(target, _max_icmp_data_size()),
                success_criteria=lambda success: success)


@contextmanager
def _enable_port_security(vnic, ovn_provider):
    ovn_port = _lookup_port_by_device_id(vnic.id, ovn_provider)
    _update_port_security(ovn_provider, ovn_port.id, enabled=True)
    try:
        yield
    finally:
        _disable_port_security(vnic, ovn_provider)


def _disable_port_security(vnic, ovn_provider):
    ovn_port = _lookup_port_by_device_id(vnic.id, ovn_provider)
    _update_port_security(ovn_provider, ovn_port.id, enabled=False)


def _lookup_port_by_device_id(vnic_id, default_ovn_provider_cloud):
    for port in default_ovn_provider_cloud.list_ports():
        device_id = port.get('device_id')
        if device_id and device_id == vnic_id:
            return port
    return None


def _update_port_security(ovn_provider, port_uuid, enabled):
    port_path = '/ports/' + str(port_uuid)
    shade_hack.hack_os_put_request(
        ovn_provider, port_path, _build_update_port_security_payload(enabled)
    )


def _build_update_port_security_payload(port_security_value):
    return {
        'port': {'port_security_enabled': port_security_value}
    }


@contextmanager
def _allow_icmp_from_host(host):
    _provision_icmp_rule(host.address, action='apply')
    try:
        yield
    finally:
        _forbid_icmp_from_host(host)


def _forbid_icmp_from_host(host):
    _provision_icmp_rule(host.address, action='remove')


def _provision_icmp_rule(source_ip, action):
    playbook_path = os.path.join(suite.playbook_dir(),
                                 action +
                                 '_icmp_rule_on_default_sec_group.yml')
    playbook = Playbook(
        playbook_path,
        extra_vars={
            'source_ip': source_ip,
            'cloud_name': 'ovirt',
            'ether_type': f'IPv{suite.af().version}'
        }
    )
    playbook.run()


def _disable_network_port_security(physnet_name, network_uuid, ovn_provider):
    _update_network_port_security(ovn_provider, physnet_name, network_uuid,
                                  enabled=False)


def _update_network_port_security(ovn_provider, physical_network_name,
                                  network_uuid, enabled):
    network_path = '/networks/' + str(network_uuid)
    update_network_payload = _build_update_physnet_port_security_payload(
        physical_network_name, enabled)
    shade_hack.hack_os_put_request(ovn_provider, network_path,
                                   update_network_payload)


def _get_network_by_name(ovn_provider, network_name):
    return ovn_provider.get_network(network_name)


def _build_update_physnet_port_security_payload(physical_network_name,
                                                port_security):
    return {
        'network': {
            'port_security_enabled': port_security,
            'provider:physical_network': physical_network_name,
            'provider:network_type': 'flat'
        }
    }


def _max_icmp_data_size():
    icmp_header_size = 8
    ip_header_size = {
        'inet': 20,
        'inet6': 40
    }
    return MTU - icmp_header_size - ip_header_size[suite.af().family]
