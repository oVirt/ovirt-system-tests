#
# Copyright 2017-2021 Red Hat, Inc.
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

from ovirtsdk4 import types

from ovirtlib import error
from ovirtlib import syncutil
from ovirtlib.sdkentity import SDKRootEntity


MiB = 2 ** 20
GiB = 2 ** 30


class ImageNotFoundError(Exception):
    pass


class DiskFormat(object):
    COW = types.DiskFormat.COW
    RAW = types.DiskFormat.RAW


class StorageType(object):

    CINDER = types.StorageType.CINDER
    FCP = types.StorageType.FCP
    GLANCE = types.StorageType.GLANCE
    GLUSTERFS = types.StorageType.GLUSTERFS
    ISCSI = types.StorageType.ISCSI
    LOCALFS = types.StorageType.LOCALFS
    NFS = types.StorageType.NFS
    POSIXFS = types.StorageType.POSIXFS


class StorageDomainType(object):

    DATA = types.StorageDomainType.DATA
    EXPORT = types.StorageDomainType.EXPORT
    IMAGE = types.StorageDomainType.IMAGE
    ISO = types.StorageDomainType.ISO
    VOLUME = types.StorageDomainType.VOLUME


class NfsVersion(object):

    AUTO = types.NfsVersion.AUTO
    V3 = types.NfsVersion.V3
    V4 = types.NfsVersion.V4
    V4_1 = types.NfsVersion.V4_1
    V4_2 = types.NfsVersion.V4_2


class HostStorageData(object):
    def __init__(
        self, storage_type, address, path, nfs_version=None, logical_units=()
    ):
        """
        :param storage_type: string indicates the storage type.
        :param address: string indicates the NFS storage address.
        :param path: string indicates the NFS storage path.
        :param nfs_version: string indicates the NFS storage version.
        :param logical_units: tuple of LogicalUnits.
        Represent logical units (luns) in case of an iSCSI storage domain.
        """
        self._type = storage_type
        self._address = address
        self._path = path
        self._nfs_version = nfs_version
        self._logical_units = logical_units

    @property
    def type(self):
        return self._type

    @property
    def address(self):
        return self._address

    @property
    def path(self):
        return self._path

    @property
    def nfs_version(self):
        return self._nfs_version

    @property
    def logical_units(self):
        return self._logical_units


class StorageDomainStatus(object):

    UNATTACHED = types.StorageDomainStatus.UNATTACHED
    ACTIVE = types.StorageDomainStatus.ACTIVE
    MAINTENANCE = types.StorageDomainStatus.MAINTENANCE


class StorageDomain(SDKRootEntity):
    @property
    def name(self):
        return self.get_sdk_type().name

    @property
    def status(self):
        return self.get_sdk_type().status

    def wait_for_unattached_status(self):
        self._wait_for_status(StorageDomainStatus.UNATTACHED)

    def create(self, name, host, domain_type, host_storage_data):
        """
        :param name: string
        :param host: hostlib.Host
        :param domain_type: StorageDomainType
        :param host_storage_data: HostStorageData
        """
        sdk_type = types.StorageDomain(
            name=name,
            host=host.get_sdk_type(),
            type=domain_type,
            storage=types.HostStorage(
                type=host_storage_data.type,
                address=host_storage_data.address,
                path=host_storage_data.path,
                nfs_version=host_storage_data.nfs_version,
                logical_units=self._get_sdk_type_logical_units(
                    host_storage_data.logical_units
                ),
            ),
        )
        self._create_sdk_entity(sdk_type)

    def destroy(self):
        self._service.remove(destroy=True)

    def destroy_sync(self):
        syncutil.sync(
            exec_func=self.destroy,
            exec_func_args=(),
            error_criteria=error.sd_destroy_error_not_due_to_busy,
        )

    def _get_parent_service(self, system):
        return system.storage_domains_service

    def _wait_for_status(self, status):
        syncutil.sync(
            exec_func=lambda: self.status,
            exec_func_args=(),
            success_criteria=lambda s: s == status,
        )

    def import_image(self, cluster, repo, image_name, template_name=None):
        """
        :type cluster: clusterlib.Cluster
        :type repo: storagelib.StorageDomain
        :type image_name: string
        :type template_name: string
        """
        images_service = repo.service.images_service()
        images = images_service.list()
        try:
            image = next(image for image in images if image.name == image_name)
        except StopIteration:
            raise ImageNotFoundError
        image_service = images_service.service(image.id)

        image_service.import_(
            import_as_template=template_name is not None,
            template=(
                types.Template(name=template_name)
                if template_name is not None
                else None
            ),
            cluster=cluster.get_sdk_type(),
            storage_domain=self.get_sdk_type(),
        )

    def create_disk(self, name):
        disk = Disk(self.system)
        disk.create(disk_name=name, sd_name=self.name)
        disk.wait_for_up_status()
        return disk

    def _get_sdk_type_logical_units(self, logical_units):
        return [
            types.LogicalUnit(
                id=lundata.id,
                address=lundata.address,
                port=lundata.port,
                target=lundata.target,
            )
            for lundata in logical_units
        ]

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'name:{self.name}, '
                f'status:{self.status}, '
                f'id:{self.id}>'
            )
        )


class Disk(SDKRootEntity):
    @property
    def status(self):
        return self.get_sdk_type().status

    def create(
        self,
        disk_name,
        sd_name,
        provisioned_size=2 * GiB,
        disk_format=DiskFormat.COW,
        status=None,
        sparse=True,
    ):
        sdk_type = types.Disk(
            name=disk_name,
            provisioned_size=provisioned_size,
            format=disk_format,
            storage_domains=[types.StorageDomain(name=sd_name)],
            status=status,
            sparse=sparse,
        )
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, system):
        return system.disks_service

    def wait_for_up_status(self):
        syncutil.sync(
            exec_func=lambda: self.status,
            exec_func_args=(),
            success_criteria=lambda s: s == types.DiskStatus.OK,
        )


class LogicalUnit(object):
    def __init__(self, id, address, port, target):
        self._id = id
        self._address = address
        self._port = port
        self._target = target

    @property
    def id(self):
        return self._id

    @property
    def address(self):
        return self._address

    @property
    def port(self):
        return self._port

    @property
    def target(self):
        return self._target


@contextlib.contextmanager
def storage_domain(system, name, domain_type, host, host_storage_data):
    sd = StorageDomain(system)
    sd.create(
        name=name,
        domain_type=domain_type,
        host=host,
        host_storage_data=host_storage_data,
    )
    try:
        sd.wait_for_unattached_status()
        yield sd
    finally:
        sd.destroy_sync()
