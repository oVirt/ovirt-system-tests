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

from lib import datacenterlib
from lib import storagelib
from lib import templatelib
from lib import virtlib


def test_run_vm_over_ipv6_nfs_storage_domain(system, default_data_center,
                                             default_cluster, host_0_up,
                                             engine_storage_ipv6):
    """
    This test verifies that:
        * it is possible to create an NFS storage domain over an ipv6 network
        * it is possible to power up a VM over such a storage domain
    """

    with ipv6_storage_domain(system, host_0_up, engine_storage_ipv6) as sd:
        with datacenterlib.attached_storage_domain(default_data_center,
                                                   sd) as sd_attached:
            with vm_down(system, default_cluster, sd_attached) as vm:
                vm.run()
                vm.wait_for_powering_up_status()


@contextlib.contextmanager
def ipv6_storage_domain(system, host, engine_storage_ipv6):
    DOMAIN_NAME = 'nfs-ipv6'
    DEFAULT_DOMAIN_PATH = '/exports/nfs/share2'

    sd = storagelib.StorageDomain(system)
    host_storage_data = storagelib.HostStorageData(
        storage_type=storagelib.StorageType.NFS,
        address='[' + engine_storage_ipv6 + ']',
        path=DEFAULT_DOMAIN_PATH,
        nfs_version=storagelib.NfsVersion.V4_2
    )
    sd.create(
        name=DOMAIN_NAME,
        domain_type=storagelib.StorageDomainType.DATA,
        host=host,
        host_storage_data=host_storage_data)
    try:
        sd.wait_for_unattached_status()
        yield sd
    finally:
        sd.destroy_sync()


@contextlib.contextmanager
def vm_down(system, default_cluster, storage_domain):
    DISK0 = 'disk0'
    VM0 = 'vm_over_ipv6_storage_domain'
    with virtlib.vm_pool(system, size=1) as (vm,):
        vm.create(vm_name=VM0,
                  cluster=default_cluster,
                  template=templatelib.TEMPLATE_BLANK)
        disk = storage_domain.create_disk(DISK0)
        disk_att_id = vm.attach_disk(disk=disk)
        vm.wait_for_disk_up_status(disk, disk_att_id)
        vm.wait_for_down_status()
        yield vm
