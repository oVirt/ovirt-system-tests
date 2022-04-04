#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import contextlib
import socket

import pytest

from fixtures.host import ETH2

from ovirtlib import clusterlib
from ovirtlib import datacenterlib
from ovirtlib import hostlib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import storagelib
from ovirtlib import templatelib
from ovirtlib import virtlib

from testlib import suite


SD_NAMES = {
    'nfs': 'nfs-ipv6',
    'iscsi': 'iscsi-ipv6',
}


@suite.skip_suites_below('4.3')
def test_non_mgmt_display_network_over_ipv6(
    system, default_data_center, default_cluster, host_0_up, nfs_storage_data, af
):
    """
    This test verifies that:
     * it is possible to create a display role over an ipv6 only network
     * it is possible to connect with a graphic display to a VM over this
       network
    """
    if not af.is6:
        return pytest.mark.skip(reason='ipv6 specific test')
    with netlib.new_network('ipv6-display-net', default_data_center) as net:
        with clusterlib.network_assignment(default_cluster, net) as cl_net:
            cl_net.set_usages((netlib.NetworkUsage.DISPLAY,))
            attach_data = netattachlib.NetworkAttachmentData(
                net, ETH2, (netattachlib.NO_V4, netattachlib.IPV6_POLY_DHCP_AUTOCONF)
            )
            with hostlib.setup_networks(host_0_up, (attach_data,)):
                host_0_up.wait_for_networks_in_sync()
                VM0 = 'vm_non_mgmt_display_net_over_ipv6'
                DSK = 'disk_non_mgmt_display_net_over_ipv6'
                with vm_powering_up(
                    system, default_data_center, default_cluster, host_0_up, nfs_storage_data, VM0, DSK
                ) as vm:
                    _try_spice_console_connect(vm)


def _try_spice_console_connect(vm):
    spice = virtlib.VmSpiceConsole(vm)
    spice.import_config()
    sock = socket.socket(socket.AF_INET6)
    try:
        sock.connect((spice.host, int(spice.port)))
    finally:
        sock.close()


@suite.xfail_suite_master('iSCSI not yet working on RHEL8')
def test_run_vm_over_ipv6_iscsi_storage_domain(
    system, default_data_center, default_cluster, host_0_up, iscsi_storage_data, af
):
    """
    This test verifies that:
        * it is possible to create an iSCSI storage domain over an ipv6 network
        * it is possible to power up a VM over such a storage domain
    """
    if not af.is6:
        return pytest.mark.skip(reason='ipv6 specific test')
    VM0 = 'vm_over_iscsi_ipv6_storage_domain'
    DSK = 'disk_over_iscsi_ipv6_storage_domain'
    with storagelib.storage_domain(system, SD_NAMES['iscsi'], host_0_up, iscsi_storage_data) as sd:
        with datacenterlib.attached_storage_domain(default_data_center, sd) as sd_attached:
            with vm_down(system, default_cluster, sd_attached, VM0, DSK) as vm:
                vm.run()
                vm.wait_for_powering_up_status()


def test_run_vm_over_ipv6_nfs_storage_domain(
    system, default_data_center, default_cluster, host_0_up, nfs_storage_data, af
):
    """
    This test verifies that:
        * it is possible to create an NFS storage domain over an ipv6 network
        * it is possible to power up a VM over such a storage domain
    """
    if not af.is6:
        return pytest.mark.skip(reason='ipv6 specific test')
    VM0 = 'vm_over_nfs_ipv6_storage_domain'
    DSK = 'disk_over_nfs_ipv6_storage_domain'
    with storagelib.storage_domain(system, SD_NAMES['nfs'], host_0_up, nfs_storage_data) as sd:
        with datacenterlib.attached_storage_domain(default_data_center, sd) as sd_attached:
            with vm_down(system, default_cluster, sd_attached, VM0, DSK) as vm:
                vm.run()
                vm.wait_for_powering_up_status()


@pytest.fixture(scope='module')
def nfs_storage_data(engine_storage_ips):
    return storagelib.NfsStorageData(f'[{engine_storage_ips[0]}]', '/exports/nfs/share2')


@pytest.fixture(scope='module')
def iscsi_storage_data(lun_id, engine_storage_ips):
    lun = storagelib.LogicalUnit(
        lun_id=lun_id, address=engine_storage_ips[0], port=3260, target='iqn.2014-07.org.ovirt:storage'
    )
    return storagelib.IscsiStorageData(logical_units=(lun,))


@contextlib.contextmanager
def vm_down(system, default_cluster, storage_domain, vm_name, disk_name):
    with virtlib.vm_pool(system, size=1) as (vm,):
        vm.create(vm_name=vm_name, cluster=default_cluster, template=templatelib.TEMPLATE_BLANK)
        disk = storage_domain.create_disk(disk_name)
        disk_att_id = vm.attach_disk(disk=disk)
        vm.wait_for_disk_up_status(disk, disk_att_id)
        vm.wait_for_down_status()
        yield vm


@contextlib.contextmanager
def vm_powering_up(system, default_data_center, default_cluster, host, nfs_storage_data, vm_name, disk_name):
    with storagelib.storage_domain(system, SD_NAMES['nfs'], host, nfs_storage_data) as sd:
        with datacenterlib.attached_storage_domain(default_data_center, sd) as sd_attached:
            with vm_down(system, default_cluster, sd_attached, vm_name, disk_name) as vm:
                vm.run()
                vm.wait_for_powering_up_status()
                yield vm
