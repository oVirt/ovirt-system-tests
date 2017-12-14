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
import pytest

from ovirtsdk4 import types

from lib import syncutil


SD_NFS_NAME = 'nfs'
SD_NFS_PATH = '/exports/nfs/share1'


@pytest.fixture(scope='session')
def storage_domains_service(system):
    return system.storage_domains_service


@pytest.fixture(scope='session')
def default_storage_domain(engine, storage_domains_service,
                           data_centers_service, default_data_center, host_0):
    sd = types.StorageDomain(
        name=SD_NFS_NAME,
        description='Default NFS storage domain',
        type=types.StorageDomainType.DATA,
        host=host_0.sdk_type,
        storage=types.HostStorage(
            type=types.StorageType.NFS,
            address=engine.ip(),
            path=SD_NFS_PATH,
            nfs_version=types.NfsVersion.V4_2,
        ),
    )
    storage_domain = _add_storage_domain(sd, storage_domains_service)
    _attach_storage_domain(
        data_centers_service, default_data_center, storage_domain)


def _add_storage_domain(sd, storage_domains_service):
    storage_domain = storage_domains_service.add(sd)
    storage_domain_service = storage_domains_service.storage_domain_service(
        storage_domain.id)

    syncutil.sync(
        exec_func=lambda: storage_domain_service.get().status,
        exec_func_args=(),
        success_criteria=lambda s: s == types.StorageDomainStatus.UNATTACHED
    )
    return storage_domain


def _attach_storage_domain(data_centers_service, default_data_center,
                           storage_domain):
    data_center_service = data_centers_service.data_center_service(
        default_data_center.id)

    attached_sds_service = data_center_service.storage_domains_service()
    attached_sds_service.add(
        types.StorageDomain(
            id=storage_domain.id,
        ),
    )
    attached_sd_service = attached_sds_service.storage_domain_service(
        storage_domain.id)

    syncutil.sync(
        exec_func=lambda: attached_sd_service.get().status,
        exec_func_args=(),
        success_criteria=lambda s: s == types.StorageDomainStatus.ACTIVE
    )
