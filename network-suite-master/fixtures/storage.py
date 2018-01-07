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
import pytest

from lib import storagelib


DEFAULT_DOMAIN_NAME = 'nfs1'
DEFAULT_DOMAIN_PATH = '/exports/nfs/share1'


@pytest.fixture(scope='session')
def default_storage_domain(system, engine, host_0_up, default_data_center):
    storage_domain = storagelib.StorageDomain(system)
    storage_domain.create(name=DEFAULT_DOMAIN_NAME,
                          domain_type=storagelib.StorageDomainType.DATA,
                          host=host_0_up,
                          host_storage_data=storagelib.HostStorageData(
                              storage_type=storagelib.StorageType.NFS,
                              address=engine.ip(),
                              path=DEFAULT_DOMAIN_PATH,
                              nfs_version=storagelib.NfsVersion.V4_2
                              )
                          )
    storage_domain.wait_for_unattached_status()

    default_data_center.attach_storage_domain(storage_domain)
    default_data_center.wait_for_sd_active_status(storage_domain)

    return storage_domain
