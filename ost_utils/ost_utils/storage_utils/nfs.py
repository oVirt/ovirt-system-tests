#
# Copyright 2020 Red Hat, Inc.
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

import ovirtsdk4 as sdk4

from ost_utils.storage_utils import domain


def add_domain(engine_api, sd_nfs_name, sd_nfs_host, sd_nfs_host_storage_ip,
               mount_path, dc_name, sd_format='v4', sd_type='data',
               nfs_version='v4_2'):
    if sd_type == 'data':
        dom_type = sdk4.types.StorageDomainType.DATA
    elif sd_type == 'iso':
        dom_type = sdk4.types.StorageDomainType.ISO
    elif sd_type == 'export':
        dom_type = sdk4.types.StorageDomainType.EXPORT

    if nfs_version == 'v3':
        nfs_vers = sdk4.types.NfsVersion.V3
    elif nfs_version == 'v4':
        nfs_vers = sdk4.types.NfsVersion.V4
    elif nfs_version == 'v4_1':
        nfs_vers = sdk4.types.NfsVersion.V4_1
    elif nfs_version == 'v4_2':
        nfs_vers = sdk4.types.NfsVersion.V4_2
    else:
        nfs_vers = sdk4.types.NfsVersion.AUTO

    p = sdk4.types.StorageDomain(
        name=sd_nfs_name,
        description='APIv4 NFS storage domain',
        type=dom_type,
        host=sd_nfs_host,
        storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.NFS,
            address=sd_nfs_host_storage_ip,
            path=mount_path,
            nfs_version=nfs_vers,
        )
    )

    domain.add(engine_api, p, dc_name)
