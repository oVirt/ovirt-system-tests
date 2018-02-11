#
# Copyright 2017 Red Hat, Inc.
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
import nose.tools as nt
from ovirtlago import testlib
import ovirtsdk4

import test_utils
from test_utils.vnic_setup import VnicSetup

DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

SD_SECOND_NFS_NAME = 'second-nfs'
VM2_NAME = 'vm2'


def _mac_value(mac):
    return int(mac.replace(':', ''), base=16)


def _get_storage_domain(root, name, service=False):
    storage_domains = root.storage_domains_service()
    # AttachedStorageDomainsService.list doesn't have the 'search' parameter
    # (StorageDomainsService.list does but this helper is overloaded)
    sd = next(sd for sd in storage_domains.list() if sd.name == name)
    return storage_domains.storage_domain_service(sd.id) if service else sd


def _get_vm_service(root, name, unregistered=None):
    virtual_machines = root.vms_service()
    # StorageDomainVmsService.list has no 'search' parameter and ignores
    # query={'name': 'spam'} so we have to do the filtering ourselves
    vm = next(vm for vm in virtual_machines.list(query={
        'unregistered': unregistered}) if vm.name == name)
    return virtual_machines.vm_service(vm.id)


@testlib.with_ovirt_api4
def deactivate_storage_domain(connection):
    VnicSetup.vnic_setup().init(connection.system_service(),
                                VM2_NAME, DC_NAME, CLUSTER_NAME)
    dc = test_utils.data_center_service(connection.system_service(), DC_NAME)

    _get_storage_domain(dc, SD_SECOND_NFS_NAME, service=True).deactivate()

    testlib.assert_equals_within_short(
        lambda: _get_storage_domain(dc, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.MAINTENANCE)


@testlib.with_ovirt_api4
def detach_storage_domain(connection):
    engine = connection.system_service()
    dc = test_utils.data_center_service(engine, DC_NAME)

    _get_storage_domain(dc, SD_SECOND_NFS_NAME, service=True).remove()

    testlib.assert_equals_within_short(
        lambda: _get_storage_domain(engine, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.UNATTACHED)


@testlib.with_ovirt_api4
def reattach_storage_domain(connection):
    VnicSetup.vnic_setup().remove_some_profiles_and_networks()
    engine = connection.system_service()
    dc = test_utils.data_center_service(engine, DC_NAME)
    sd = _get_storage_domain(engine, SD_SECOND_NFS_NAME)

    dc.storage_domains_service().add(sd)

    testlib.assert_equals_within_short(
        lambda: _get_storage_domain(dc, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.ACTIVE)


@testlib.with_ovirt_api4
def import_lost_vm(connection):
    engine = connection.system_service()
    sd = _get_storage_domain(engine, SD_SECOND_NFS_NAME, service=True)
    lost_vm = _get_vm_service(sd, VM2_NAME, unregistered=True)

    rg = VnicSetup.vnic_setup().registration_configuration
    lost_vm.register(
        allow_partial_import=True,
        registration_configuration=rg,
        cluster=ovirtsdk4.types.Cluster(name=CLUSTER_NAME),
        vm=ovirtsdk4.types.Vm(name=VM2_NAME),
        reassign_bad_macs=True)

    vm = _get_vm_service(engine, VM2_NAME)
    vm_nic = vm.nics_service().list()[0]
    mac_address = _mac_value(vm_nic.mac.address)

    default_mac_pool = engine.mac_pools_service().list()[0]
    mac_range = default_mac_pool.ranges[0]

    nt.assert_greater_equal(mac_address, _mac_value(mac_range.from_))
    nt.assert_less_equal(mac_address, _mac_value(mac_range.to))
    VnicSetup.vnic_setup().assert_results(VM2_NAME, CLUSTER_NAME)


_TEST_LIST = [
    deactivate_storage_domain,
    detach_storage_domain,
    reattach_storage_domain,
    import_lost_vm,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
