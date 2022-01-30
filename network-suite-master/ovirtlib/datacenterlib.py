#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import contextlib

from ovirtsdk4 import types

from . import error
from . import netlib
from . import storagelib
from . import syncutil
from .error import report_status
from .sdkentity import SDKRootEntity


class DataCenter(SDKRootEntity):
    @property
    def name(self):
        return self.get_sdk_type().name

    @property
    def status(self):
        return self.get_sdk_type().status

    def attach_storage_domain(self, sd):
        sds_service = self._service.storage_domains_service()
        sds_service.add(sd.get_sdk_type())

    def deactivate_storage_domain(self, sd):
        self._sd_service(sd).deactivate()

    def deactivate_storage_domain_sync(self, sd):
        syncutil.sync(
            exec_func=self.deactivate_storage_domain,
            exec_func_args=(sd,),
            error_criteria=error.sd_deactivation_error_not_due_to_busy,
        )

    def list_qos(self):
        qos_entities = []
        for qos in self._service.qoss_service().list():
            qos_entity = netlib.QoS(self)
            qos_entity.import_by_name(name=qos.name)
            qos_entities.append(qos_entity)
        return qos_entities

    def remove_qos(self, qos_names):
        for qos in self.list_qos():
            if qos.name in qos_names:
                self._service.qoss_service().qos_service(qos.id).remove()

    @report_status
    def wait_for_up_status(self):
        self._wait_for_status(types.DataCenterStatus.UP)

    def wait_for_sd_active_status(self, sd):
        self._wait_for_sd_status(sd, storagelib.StorageDomainStatus.ACTIVE)

    def wait_for_sd_maintenance_status(self, sd):
        self._wait_for_sd_status(sd, storagelib.StorageDomainStatus.MAINTENANCE)

    def create(self, dc_name):
        sdk_type = types.DataCenter(name=dc_name)
        self._create_sdk_entity(sdk_type)

    def get_mgmt_network(self):
        ovirtmgmt = netlib.Network(self)
        ovirtmgmt.import_by_name(netlib.OVIRTMGMT)
        return ovirtmgmt

    def _get_parent_service(self, system):
        return system.data_centers_service

    def _wait_for_sd_status(self, sd, status):
        sd_service = self._sd_service(sd)
        syncutil.sync(
            exec_func=lambda: sd_service.get().status,
            exec_func_args=(),
            success_criteria=lambda s: s == status,
        )

    def _sd_service(self, sd):
        return self._service.storage_domains_service().service(sd.id)

    def _wait_for_status(self, status):
        syncutil.sync(
            exec_func=lambda: self.status,
            exec_func_args=(),
            success_criteria=lambda s: s == status,
            timeout=60 * 5,
        )

    @staticmethod
    def iterate(system, search=None):
        """Iterate over `system`'s data centers

        If `search` is None, all data centers are iterated. Otherwise,
        `search` should be a search query string understood by oVirt.
        Cf. http://ovirt.github.io/ovirt-engine-api-model/master/#_searching
        """
        for sdk_obj in system.data_centers_service.list(search=search):
            dc = DataCenter(system)
            dc.import_by_id(sdk_obj.id)
            yield dc

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (f'<{self.__class__.__name__}| ' f'name:{self.name} ' f'status:{self.status}, ' f'id:{self.id}>')
        )


@contextlib.contextmanager
def attached_storage_domain(data_center, storage_domain):
    data_center.attach_storage_domain(storage_domain)
    try:
        # assuming that even if the storage does not become active,
        # deactivate will not fail:
        data_center.wait_for_sd_active_status(storage_domain)
        yield storage_domain
    finally:
        data_center.deactivate_storage_domain_sync(storage_domain)
        data_center.wait_for_sd_maintenance_status(storage_domain)
