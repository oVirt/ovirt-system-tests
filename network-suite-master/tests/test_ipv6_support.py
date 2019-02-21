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
import contextlib
import socket

from ovirtlib import clusterlib
from ovirtlib import datacenterlib
from ovirtlib import hostlib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import storagelib
from ovirtlib import templatelib
from ovirtlib import virtlib

from ovirtlib.storagelib import storage_domain
from testlib import suite


@suite.SKIP_SUITE_42
def test_non_mgmt_display_network_over_ipv6(system, default_data_center,
                                            default_cluster, host_0_up,
                                            host0_eth1_ipv6, host0_eth2_ipv6,
                                            engine_storage_ipv6):
    """
    This test verifies that:
     * it is possible to create a display role over an ipv6 only network
     * it is possible to connect with a graphic display to a VM over this
       network
    Note: host0_eth1_ipv6 fixture is mandatory because if there is no ipv6
          address on eth1 of the host, connection with the storage server
          cannot be maintained
    """
    assert host0_eth1_ipv6 != ''
    with netlib.new_network('ipv6-disp_net', default_data_center) as net:
        with clusterlib.network_assignment(default_cluster, net) as cl_net:
            cl_net.set_usages((netlib.NetworkUsage.DISPLAY,))
            no_v4 = netattachlib.NoIpAssignment()
            v6_no_gw = netattachlib.StaticIpAssignment(
                version=netattachlib.IpVersion.V6,
                addr=host0_eth2_ipv6,
                mask='64',
            )
            attach_data = netattachlib.NetworkAttachmentData(
                net, 'eth2', (no_v4, v6_no_gw)
            )
            with hostlib.setup_networks(host_0_up, (attach_data,)):
                host_0_up.wait_for_networks_in_sync()
                VM0 = 'vm_non_mgmt_display_net_over_ipv6'
                DSK = 'disk_non_mgmt_display_net_over_ipv6'
                with vm_powering_up(system, default_data_center,
                                    default_cluster, host_0_up,
                                    engine_storage_ipv6, VM0, DSK) as vm:
                    _try_spice_console_connect(vm)


def _try_spice_console_connect(vm):
    spice = virtlib.VmSpiceConsole(vm)
    spice.import_config()
    sock = socket.socket(socket.AF_INET6)
    try:
        sock.connect((spice.host, int(spice.port)))
    finally:
        sock.close()


def test_run_vm_over_ipv6_iscsi_storage_domain(system, default_data_center,
                                               default_cluster, host_0_up,
                                               engine_storage_ipv6, lun_id):
    """
    This test verifies that:
        * it is possible to create an iSCSI storage domain over an ipv6 network
        * it is possible to power up a VM over such a storage domain
    """
    VM0 = 'vm_over_iscsi_ipv6_storage_domain'
    DSK = 'disk_over_iscsi_ipv6_storage_domain'
    with ipv6_iscsi_storage_domain(system, host_0_up, engine_storage_ipv6,
                                   lun_id) as sd:
        with datacenterlib.attached_storage_domain(default_data_center,
                                                   sd) as sd_attached:
            with vm_down(system, default_cluster, sd_attached, VM0, DSK) as vm:
                vm.run()
                vm.wait_for_powering_up_status()


def test_run_vm_over_ipv6_nfs_storage_domain(system, default_data_center,
                                             default_cluster, host_0_up,
                                             engine_storage_ipv6):
    """
    This test verifies that:
        * it is possible to create an NFS storage domain over an ipv6 network
        * it is possible to power up a VM over such a storage domain
    """
    VM0 = 'vm_over_nfs_ipv6_storage_domain'
    DSK = 'disk_over_nfs_ipv6_storage_domain'
    with ipv6_nfs_storage_domain(system, host_0_up, engine_storage_ipv6) as sd:
        with datacenterlib.attached_storage_domain(default_data_center,
                                                   sd) as sd_attached:
            with vm_down(system, default_cluster, sd_attached, VM0, DSK) as vm:
                vm.run()
                vm.wait_for_powering_up_status()


@contextlib.contextmanager
def ipv6_nfs_storage_domain(system, host, engine_storage_ipv6):
    DOMAIN_NAME = 'nfs-ipv6'
    DEFAULT_DOMAIN_PATH = '/exports/nfs/share2'

    sd = storagelib.StorageDomain(system)
    host_storage_data = storagelib.HostStorageData(
        storage_type=storagelib.StorageType.NFS,
        address='[' + engine_storage_ipv6 + ']',
        path=DEFAULT_DOMAIN_PATH,
        nfs_version=storagelib.NfsVersion.V4_2
    )

    with storage_domain(system, DOMAIN_NAME, storagelib.StorageDomainType.DATA,
                        host, host_storage_data) as sd:
        yield sd


@contextlib.contextmanager
def ipv6_iscsi_storage_domain(system, host, engine_storage_ipv6, lun_id):
    DOMAIN_NAME = 'iscsi-ipv6'
    ISCSI_ADDRESS = engine_storage_ipv6
    ISCSI_PORT = 3260
    ISCSI_TARGET = 'iqn.2014-07.org.ovirt:storage'

    lun = storagelib.LogicalUnit(
        id=lun_id,
        address=ISCSI_ADDRESS,
        port=ISCSI_PORT,
        target=ISCSI_TARGET,
    )

    host_storage_data = storagelib.HostStorageData(
        storage_type=storagelib.StorageType.ISCSI,
        address=None,
        path=None,
        logical_units=(lun,))

    with storage_domain(system, DOMAIN_NAME, storagelib.StorageDomainType.DATA,
                        host, host_storage_data) as sd:
        yield sd


@contextlib.contextmanager
def vm_down(system, default_cluster, storage_domain, vm_name, disk_name):
    with virtlib.vm_pool(system, size=1) as (vm,):
        vm.create(vm_name=vm_name,
                  cluster=default_cluster,
                  template=templatelib.TEMPLATE_BLANK)
        disk = storage_domain.create_disk(disk_name)
        disk_att_id = vm.attach_disk(disk=disk)
        vm.wait_for_disk_up_status(disk, disk_att_id)
        vm.wait_for_down_status()
        yield vm


@contextlib.contextmanager
def vm_powering_up(system, default_data_center, default_cluster,
                   host, engine_storage_ipv6, vm_name, disk_name):
    with ipv6_nfs_storage_domain(system, host, engine_storage_ipv6) as sd:
        with datacenterlib.attached_storage_domain(default_data_center,
                                                   sd) as sd_attached:
            with vm_down(system, default_cluster, sd_attached, vm_name,
                         disk_name) as vm:
                vm.run()
                vm.wait_for_powering_up_status()
                yield vm
