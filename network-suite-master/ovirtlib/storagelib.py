#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import abc
import contextlib

from ovirtsdk4 import types

from . import error
from . import syncutil
from .sdkentity import SDKRootEntity


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


class HostStorageData(metaclass=abc.ABCMeta):
    def __init__(self, storage_type, domain_type, address=None, path=None):
        """
        :param storage_type: storagelib.StorageType
        :param domain_type: storagelib.StorageDomainType
        :param address: string indicates the storage address.
        :param path: string indicates the storage path.
        """
        self._storage_type = storage_type
        self._domain_type = domain_type
        self._address = address
        self._path = path

    @property
    def storage_type(self):
        return self._storage_type

    @property
    def domain_type(self):
        return self._domain_type

    @property
    def address(self):
        return self._address

    @property
    def path(self):
        return self._path

    @abc.abstractmethod
    def as_sdk_type(self):
        """
        :return: representation of this object as the equivalent ovirtsdk4.types object.
        ovirtlib is a wrapper and encapsulator of ovirtsdk4.types and ovirtsdk4.services,
        so this method should not be used outside ovirtlib
        """


class NfsStorageData(HostStorageData):
    def __init__(self, address, path, domain_type=StorageDomainType.DATA, version=NfsVersion.V4_2):
        super(NfsStorageData, self).__init__(StorageType.NFS, domain_type, address, path)
        self._version = version

    @property
    def version(self):
        return self._version

    def as_sdk_type(self):
        return types.HostStorage(
            type=self.storage_type,
            address=self.address,
            path=self.path,
            nfs_version=self.version,
        )

    def __repr__(self):
        return (
            f'<{self.__class__.__name__}| '
            f'address:{self.address}, '
            f'path:{self.path}, '
            f'version:{self.version}>'
            f'domain_type:{self.domain_type}, '
        )


class IscsiStorageData(HostStorageData):
    def __init__(self, domain_type=StorageDomainType.DATA, logical_units=()):
        super(IscsiStorageData, self).__init__(StorageType.ISCSI, domain_type)
        self._logical_units = logical_units

    @property
    def logical_units(self):
        return self._logical_units

    def as_sdk_type(self):
        return types.HostStorage(
            type=self.storage_type,
            address=self.address,
            path=self.path,
            logical_units=[lun.as_sdk_type() for lun in self.logical_units],
        )

    def __repr__(self):
        return f'<{self.__class__.__name__}| logical_units:{self.logical_units}, domain_type:{self.domain_type}>'


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

    def create(self, name, host, host_storage_data):
        """
        :param name: string
        :param host: hostlib.Host
        :param host_storage_data: HostStorageData
        """
        sdk_type = types.StorageDomain(
            name=name,
            host=host.get_sdk_type(),
            type=host_storage_data.domain_type,
            storage=host_storage_data.as_sdk_type(),
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
            template=(types.Template(name=template_name) if template_name is not None else None),
            cluster=cluster.get_sdk_type(),
            storage_domain=self.get_sdk_type(),
        )

    def create_disk(self, name):
        disk = Disk(self.system)
        disk.create(disk_name=name, sd_name=self.name)
        disk.wait_for_up_status()
        return disk

    def __repr__(self):
        return self._execute_without_raising(
            lambda: f'<{self.__class__.__name__}| name:{self.name}, status:{self.status}, id:{self.id}>'
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
    def __init__(self, lun_id, address, port, target):
        self._id = lun_id
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

    def as_sdk_type(self):
        return types.LogicalUnit(id=self.id, address=self.address, port=self.port, target=self.target)

    def __repr__(self):
        return (
            f'<{self.__class__.__name__}| '
            f'address:{self.address}, '
            f'port:{self.port}, '
            f'target:{self.target}, '
            f'lun_id:{self.id}>'
        )


@contextlib.contextmanager
def storage_domain(system, name, host, host_storage_data):
    sd = StorageDomain(system)
    sd.create(
        name=name,
        host=host,
        host_storage_data=host_storage_data,
    )
    try:
        sd.wait_for_unattached_status()
        yield sd
    finally:
        sd.destroy_sync()
