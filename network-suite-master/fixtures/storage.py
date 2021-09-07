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

import pytest

from ovirtlib import sshlib
from ovirtlib import storagelib
from ovirtlib.sdkentity import EntityNotFoundError


DEFAULT_DOMAIN_NAME = 'nfs1'
DEFAULT_DOMAIN_PATH = '/exports/nfs/share1'


@pytest.fixture(scope='session')
def default_storage_domain(
    system, engine_facts, host_0_up, default_data_center
):
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
                address=engine_facts.default_ip(urlize=True),
                path=DEFAULT_DOMAIN_PATH,
                nfs_version=storagelib.NfsVersion.V4_2,
            ),
        )
        storage_domain.wait_for_unattached_status()
        default_data_center.attach_storage_domain(storage_domain)
    default_data_center.wait_for_sd_active_status(storage_domain)
    return storage_domain


@pytest.fixture(scope='session')
def lun_id(engine_facts):
    # Reads a lun id value from the file
    node = sshlib.Node(engine_facts.default_ip(), engine_facts.ssh_password)
    ret = node.exec_command(' '.join(['cat', '/root/multipath.txt']))
    assert ret.code == 0
    return ret.out.splitlines()[0]
