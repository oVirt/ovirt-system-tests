#
# Copyright 2017-2018 Red Hat, Inc.
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
from ovirtsdk4 import types

from lib import netlib
from lib import storagelib
from lib import syncutil
from lib.sdkentity import SDKRootEntity


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

    def wait_for_up_status(self):
        self._wait_for_status(types.DataCenterStatus.UP)

    def wait_for_sd_active_status(self, sd):
        self._wait_for_sd_status(sd, storagelib.StorageDomainStatus.ACTIVE)

    def create(self, dc_name):
        sdk_type = types.DataCenter(name=dc_name)
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, system):
        return system.data_centers_service

    def _wait_for_sd_status(self, sd, status):
        sd_service = self._service.storage_domains_service().service(sd.id)
        syncutil.sync(exec_func=lambda: sd_service.get().status,
                      exec_func_args=(),
                      success_criteria=lambda s: s == status)

    def _wait_for_status(self, status):
        syncutil.sync(exec_func=lambda: self.status,
                      exec_func_args=(),
                      success_criteria=lambda s: s == status,
                      timeout=60 * 5)
