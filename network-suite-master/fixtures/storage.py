#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import pytest

from ovirtlib import sshlib
from ovirtlib import storagelib
from ovirtlib.sdkentity import EntityNotFoundError


DEFAULT_DOMAIN_NAME = 'nfs1'
DEFAULT_DOMAIN_PATH = '/exports/nfs/share1'


@pytest.fixture(scope='session')
def default_storage_domain(system, storage_facts, host_0_up, default_data_center):
    host_0_up.workaround_bz_1779280()
    storage_domain = storagelib.StorageDomain(system)
    try:
        storage_domain.import_by_name(DEFAULT_DOMAIN_NAME)
    except EntityNotFoundError:
        storage_domain.create(
            name=DEFAULT_DOMAIN_NAME,
            domain_type=storagelib.StorageDomainType.DATA,
            host=host_0_up,
            host_storage_data=storagelib.HostStorageData(
                storage_type=storagelib.StorageType.NFS,
                address=storage_facts.default_ip(urlize=True),
                path=DEFAULT_DOMAIN_PATH,
                nfs_version=storagelib.NfsVersion.V4_2,
            ),
        )
        storage_domain.wait_for_unattached_status()
        default_data_center.attach_storage_domain(storage_domain)
    default_data_center.wait_for_sd_active_status(storage_domain)
    return storage_domain


@pytest.fixture(scope='session')
def lun_id(storage_facts):
    # Reads a lun id value from the file
    node = sshlib.Node(storage_facts.default_ip(), storage_facts.ssh_password)
    ret = node.exec_command(' '.join(['cat', '/root/multipath.txt']))
    assert ret.code == 0
    return ret.out.splitlines()[0]
