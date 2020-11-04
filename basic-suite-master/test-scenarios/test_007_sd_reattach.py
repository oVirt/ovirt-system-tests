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
from __future__ import absolute_import

import ovirtsdk4

import test_utils
from test_utils.constants import FLOATING_DISK_NAME
from ost_utils import assertions
from ost_utils.pytest import order_by
from ost_utils.pytest.fixtures.engine import *
# TODO: uncomment once VnicSetup checks are fixed.
# from test_utils.vnic_setup import VnicSetup

DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

SD_SECOND_NFS_NAME = 'second-nfs'
VM2_NAME = 'vm2'


_TEST_LIST = [
    "test_deactivate_storage_domain",
    "test_detach_storage_domain",
    "test_reattach_storage_domain",
    "test_import_lost_vm",
    "test_import_floating_disk"
]


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


def _get_floating_disk_service(root, name, unregistered=None):
    disks = root.disks_service()
    disk = next(disk for disk in disks.list(query={
        'unregistered': unregistered}) if disk.name == name)
    return disks.disk_service(disk.id)


@order_by(_TEST_LIST)
def test_deactivate_storage_domain(engine_api):
    # TODO: uncomment once VnicSetup checks are fixed.
    # TODO: this also seems to leave running tasks behind which break the deactivation.
    # TODO: it should be tested in multiple runs or properly waited for.
    # VnicSetup.vnic_setup().init(engine_api.system_service(),
    #                            VM2_NAME, DC_NAME, CLUSTER_NAME)
    dc = test_utils.data_center_service(engine_api.system_service(), DC_NAME)

    _get_storage_domain(dc, SD_SECOND_NFS_NAME, service=True).deactivate()

    assertions.assert_equals_within_short(
        lambda: _get_storage_domain(dc, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.MAINTENANCE)


@order_by(_TEST_LIST)
def test_detach_storage_domain(engine_api):
    engine = engine_api.system_service()
    dc = test_utils.data_center_service(engine, DC_NAME)

    _get_storage_domain(dc, SD_SECOND_NFS_NAME, service=True).remove()

    assertions.assert_equals_within_short(
        lambda: _get_storage_domain(engine, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.UNATTACHED)


@order_by(_TEST_LIST)
def test_reattach_storage_domain(engine_api):
    # TODO: uncomment once VnicSetup checks are fixed.
    # VnicSetup.vnic_setup().remove_some_profiles_and_networks()
    engine = engine_api.system_service()
    dc = test_utils.data_center_service(engine, DC_NAME)
    sd = _get_storage_domain(engine, SD_SECOND_NFS_NAME)

    dc.storage_domains_service().add(sd)

    assertions.assert_equals_within_short(
        lambda: _get_storage_domain(dc, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.ACTIVE)


@order_by(_TEST_LIST)
def test_import_lost_vm(engine_api):
    engine = engine_api.system_service()
    sd = _get_storage_domain(engine, SD_SECOND_NFS_NAME, service=True)
    lost_vm = _get_vm_service(sd, VM2_NAME, unregistered=True)

    # TODO: uncomment once VnicSetup checks are fixed.
    # rg = VnicSetup.vnic_setup().registration_configuration
    lost_vm.register(
        allow_partial_import=True,
        # TODO: uncomment once VnicSetup checks are fixed.
        # registration_configuration=rg,
        cluster=ovirtsdk4.types.Cluster(name=CLUSTER_NAME),
        vm=ovirtsdk4.types.Vm(name=VM2_NAME),
        reassign_bad_macs=True)

    vm = _get_vm_service(engine, VM2_NAME)
    vm_nic = vm.nics_service().list()[0]
    mac_address = _mac_value(vm_nic.mac.address)

    default_mac_pool = engine.mac_pools_service().list()[0]
    mac_range = default_mac_pool.ranges[0]

    assert mac_address >= _mac_value(mac_range.from_)
    assert mac_address <= _mac_value(mac_range.to)
    # TODO: uncomment once VnicSetup checks are fixed.
    # VnicSetup.vnic_setup().assert_results(VM2_NAME, CLUSTER_NAME)


@order_by(_TEST_LIST)
def test_import_floating_disk(engine_api):
    engine = engine_api.system_service()
    dc_service = test_utils.data_center_service(engine, DC_NAME)
    attached_sds_service = dc_service.storage_domains_service()
    sd_service = _get_storage_domain(engine, SD_SECOND_NFS_NAME, service=False)
    attached_domain = attached_sds_service.storage_domain_service(
        sd_service.id)

    disk = _get_floating_disk_service(
        attached_domain, FLOATING_DISK_NAME, unregistered=True)
    disk.register()
    registered_disk = _get_floating_disk_service(
        attached_domain, FLOATING_DISK_NAME)
    assert registered_disk.get().name == FLOATING_DISK_NAME
