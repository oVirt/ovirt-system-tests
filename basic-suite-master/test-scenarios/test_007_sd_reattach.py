#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from __future__ import absolute_import

import ovirtsdk4

import pytest

from ost_utils import assert_utils
from ost_utils import engine_utils
from ost_utils import test_utils
from ost_utils.constants import FLOATING_DISK_NAME
from ost_utils.pytest import order_by
from ost_utils.pytest.fixtures.sdk import *
from ost_utils.vnic_setup import VnicSetup

DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

SD_SECOND_NFS_NAME = 'second-nfs'
VM2_NAME = 'vm2'

_TEST_LIST = [
    "test_deactivate_storage_domain",
    "test_detach_storage_domain",
    "test_reattach_storage_domain",
    "test_import_lost_vm",
    "test_import_floating_disk",
]


def _mac_value(mac):
    return int(mac.replace(':', ''), base=16)


@order_by(_TEST_LIST)
def test_deactivate_storage_domain(engine_api):
    # TODO: this also seems to leave running tasks behind which break the deactivation.
    # TODO: it should be tested in multiple runs or properly waited for.
    VnicSetup.vnic_setup().init(engine_api.system_service(), VM2_NAME, DC_NAME, CLUSTER_NAME)
    engine = engine_api.system_service()
    dc = test_utils.data_center_service(engine_api.system_service(), DC_NAME)
    correlation_id = 'deactivate_storage_domain'

    def _deactivate_with_running_ovf_update_task():
        try:
            test_utils.get_attached_storage_domain(dc, SD_SECOND_NFS_NAME, service=True).deactivate(
                query={'correlation_id': correlation_id}
            )
            return True
        except ovirtsdk4.Error as err:
            # The storage domain's deactivation may fail if it has running tasks.
            # In case of updating ovf_store disks task (UploadStream),
            # ignore. Otherwise, raise the exception.
            if not (('UploadStream' in err.args[0]) or ('OVF' in err.args[0])):
                raise
            return False

    def _is_deactivation_job_finished():
        deactivation_job_statuses = engine_utils.get_jobs_statuses(engine, correlation_id)
        return (ovirtsdk4.types.JobStatus.FINISHED in deactivation_job_statuses) and not (
            ovirtsdk4.types.JobStatus.STARTED in deactivation_job_statuses
        )

    assert assert_utils.true_within_short(_deactivate_with_running_ovf_update_task)

    # Wait for the storage deactivation to be finished.
    assert assert_utils.true_within_short(_is_deactivation_job_finished)

    assert assert_utils.equals_within_short(
        lambda: test_utils.get_attached_storage_domain(dc, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.MAINTENANCE,
    )


@order_by(_TEST_LIST)
def test_detach_storage_domain(engine_api):
    engine = engine_api.system_service()
    dc = test_utils.data_center_service(engine, DC_NAME)

    test_utils.get_attached_storage_domain(dc, SD_SECOND_NFS_NAME, service=True).remove()

    assert assert_utils.equals_within_short(
        lambda: test_utils.get_attached_storage_domain(engine, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.UNATTACHED,
    )


@order_by(_TEST_LIST)
def test_reattach_storage_domain(engine_api):
    VnicSetup.vnic_setup().remove_some_profiles_and_networks()
    engine = engine_api.system_service()
    dc = test_utils.data_center_service(engine, DC_NAME)
    sd = test_utils.get_attached_storage_domain(engine, SD_SECOND_NFS_NAME)

    dc.storage_domains_service().add(sd)

    assert assert_utils.equals_within_short(
        lambda: test_utils.get_attached_storage_domain(dc, SD_SECOND_NFS_NAME).status,
        ovirtsdk4.types.StorageDomainStatus.ACTIVE,
    )


@order_by(_TEST_LIST)
@pytest.mark.skipif(True, reason="test disabled temporarily to investigate hanging vdsm problem")
def test_import_lost_vm(engine_api):
    engine = engine_api.system_service()
    sd = test_utils.get_attached_storage_domain(engine, SD_SECOND_NFS_NAME, service=True)
    lost_vm = test_utils.get_storage_domain_vm_service_by_query(sd, VM2_NAME, query={'unregistered': True})

    rg = VnicSetup.vnic_setup().registration_configuration
    lost_vm.register(
        allow_partial_import=True,
        registration_configuration=rg,
        cluster=ovirtsdk4.types.Cluster(name=CLUSTER_NAME),
        vm=ovirtsdk4.types.Vm(name=VM2_NAME),
        reassign_bad_macs=True,
    )

    vm = test_utils.get_storage_domain_vm_service_by_name(engine, VM2_NAME)
    vm_nic = vm.nics_service().list()[0]
    mac_address = _mac_value(vm_nic.mac.address)

    default_mac_pool = engine.mac_pools_service().list()[0]
    mac_range = default_mac_pool.ranges[0]

    assert mac_address >= _mac_value(mac_range.from_)
    assert mac_address <= _mac_value(mac_range.to)
    VnicSetup.vnic_setup().assert_results(VM2_NAME, CLUSTER_NAME)


@order_by(_TEST_LIST)
@pytest.mark.skipif(True, reason="test disabled temporarily to investigate hanging vdsm problem")
def test_import_floating_disk(engine_api):
    engine = engine_api.system_service()
    dc_service = test_utils.data_center_service(engine, DC_NAME)
    attached_sds_service = dc_service.storage_domains_service()
    sd_service = test_utils.get_attached_storage_domain(engine, SD_SECOND_NFS_NAME, service=False)
    attached_domain = attached_sds_service.storage_domain_service(sd_service.id)

    disk = test_utils.get_attached_storage_domain_disk_service(
        attached_domain, FLOATING_DISK_NAME, query={'unregistered': True}
    )
    disk.register()
    registered_disk = test_utils.get_attached_storage_domain_disk_service(attached_domain, FLOATING_DISK_NAME)
    assert registered_disk.get().name == FLOATING_DISK_NAME
