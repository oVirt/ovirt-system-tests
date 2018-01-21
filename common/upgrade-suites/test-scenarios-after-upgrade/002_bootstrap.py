#
# Copyright 2014, 2017 Red Hat, Inc.
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
import os
import random

import nose.tools as nt
from ovirtsdk.xml import params

# TODO: import individual SDKv4 types directly (but don't forget sdk4.Error)
import ovirtsdk4 as sdk4

from lago import utils
from ovirtlago import testlib
from test_utils import constants

API_V3_ONLY = os.getenv('API_V3_ONLY', False)
if API_V3_ONLY:
    API_V4 = False
else:
    API_V4 = True

# DC/Cluster
DC_NAME = 'test-dc'
DC_VER_MAJ = 4
DC_VER_MIN = 0
SD_FORMAT = 'v4'
CLUSTER_NAME = 'test-cluster'
DC_QUOTA_NAME = 'DC-QUOTA'

# Storage
MASTER_SD_TYPE = 'iscsi'

SD_NFS_NAME = 'nfs'
SD_SECOND_NFS_NAME = 'second-nfs'
SD_NFS_HOST_NAME = testlib.get_prefixed_name('engine')
SD_NFS_PATH = '/exports/nfs/share1'
SD_SECOND_NFS_PATH = '/exports/nfs/share2'

SD_ISCSI_NAME = 'iscsi'
SD_ISCSI_HOST_NAME = testlib.get_prefixed_name('engine')
SD_ISCSI_TARGET = 'iqn.2014-07.org.ovirt:storage'
SD_ISCSI_PORT = 3260
SD_ISCSI_NR_LUNS = 2

SD_ISO_NAME = 'iso'
SD_ISO_HOST_NAME = SD_NFS_HOST_NAME
SD_ISO_PATH = '/exports/nfs/iso'

SD_TEMPLATES_NAME = 'templates'
SD_TEMPLATES_HOST_NAME = SD_NFS_HOST_NAME
SD_TEMPLATES_PATH = '/exports/nfs/exported'

SD_GLANCE_NAME = 'ovirt-image-repository'
GLANCE_AVAIL = False
CIRROS_IMAGE_NAME = 'CirrOS 0.3.5 for x86_64'
GLANCE_SERVER_URL = 'http://glance.ovirt.org:9292/'


def _get_host_ip(prefix, host_name):
    return prefix.virt_env.get_vm(host_name).ip()


def _hosts_in_dc(api, dc_name=DC_NAME):
    hosts = api.hosts.list(query='datacenter={} AND status=up'.format(dc_name))
    if hosts:
        return sorted(hosts, key=lambda host: host.name)
    raise RuntimeError('Could not find hosts that are up in DC %s' % dc_name)


def _hosts_in_dc_4(api, dc_name=DC_NAME):
    hosts_service = api.system_service().hosts_service()
    query = 'datacenter={} AND status=up'
    hosts = hosts_service.list(search=query.format(dc_name))
    if hosts:
        return sorted(hosts, key=lambda host: host.name)
    raise RuntimeError('Could not find hosts that are up in DC %s' % dc_name)


def _random_host_from_dc(api, dc_name=DC_NAME):
    return random.choice(_hosts_in_dc(api, dc_name))


def _random_host_from_dc_4(api, dc_name=DC_NAME):
    return random.choice(_hosts_in_dc_4(api, dc_name))


@testlib.with_ovirt_api4
def add_dc(api):
    dcs_service = api.system_service().data_centers_service()
    nt.assert_true(
         dcs_service.add(
            sdk4.types.DataCenter(
                name=DC_NAME,
                description='APIv4 DC',
                local=False,
                version=sdk4.types.Version(major=DC_VER_MAJ, minor=DC_VER_MIN),
            ),
         )
    )


@testlib.with_ovirt_prefix
def add_cluster(prefix):
    api = prefix.virt_env.engine_vm().get_api(api_ver=4)
    clusters_service = api.system_service().clusters_service()
    nt.assert_true(
        clusters_service.add(
            sdk4.types.Cluster(
                name=CLUSTER_NAME,
                description='APIv4 Cluster',
                data_center=sdk4.types.DataCenter(
                    name=DC_NAME,
                ),
                ballooning_enabled=True,
            ),
        )
    )


@testlib.with_ovirt_prefix
def add_hosts(prefix):
    api = prefix.virt_env.engine_vm().get_api_v4()
    hosts_service = api.system_service().hosts_service()

    def _add_host_4(vm):
        return hosts_service.add(
            sdk4.types.Host(
                name=vm.name(),
                description='host %s' % vm.name(),
                address=vm.name(),
                root_password=str(vm.root_password()),
                override_iptables=True,
                cluster=sdk4.types.Cluster(
                    name=CLUSTER_NAME,
                ),
            ),
        )

    def _host_is_up_4():
        host_service = hosts_service.host_service(api_host.id)
        host_obj = host_service.get()

        if host_obj.status == sdk4.types.HostStatus.INSTALLING:
            return False

        if host_obj.status == sdk4.types.HostStatus.UP:
            return True

        if host_obj.status == sdk4.types.HostStatus.NON_OPERATIONAL:
            raise RuntimeError('Host %s is in non operational state' %
                               api_host.name)
        if host_obj.status == sdk4.types.HostStatus.INSTALL_FAILED:
            raise RuntimeError('Host %s installation failed' % api_host.name)
        if host_obj.status == sdk4.types.HostStatus.NON_RESPONSIVE:
            raise RuntimeError('Host %s is in non responsive state' %
                               api_host.name)

    hosts = prefix.virt_env.host_vms()
    vec = utils.func_vector(_add_host_4, [(h,) for h in hosts])
    vt = utils.VectorThread(vec)
    vt.start_all()
    nt.assert_true(all(vt.join_all()))

    api_hosts = hosts_service.list()
    for api_host in api_hosts:
        testlib.assert_true_within(_host_is_up_4, timeout=constants.ADD_HOST_TIMEOUT)

    for host in hosts:
        host.ssh(['rm', '-rf', '/dev/shm/yum', '/dev/shm/*.rpm'])


def _add_storage_domain_3(api, p):
    dc = api.datacenters.get(DC_NAME)
    sd = api.storagedomains.add(p)
    nt.assert_true(sd)
    nt.assert_true(
        api.datacenters.get(
            DC_NAME,
        ).storagedomains.add(
            api.storagedomains.get(
                sd.name,
            ),
        )
    )

    if dc.storagedomains.get(sd.name).status.state == 'maintenance':
        sd.activate()
    testlib.assert_true_within_long(
        lambda: dc.storagedomains.get(sd.name).status.state == 'active'
    )


def _add_storage_domain_4(api, p):
    sds_service = api.system_service().storage_domains_service()
    sd = sds_service.add(p)

    sd_service = sds_service.storage_domain_service(sd.id)
    testlib.assert_true_within_long(
        lambda: sd_service.get().status ==
        sdk4.types.StorageDomainStatus.UNATTACHED
    )

    dcs_service = api.system_service().data_centers_service()
    dc = dcs_service.list(search='name=%s' % DC_NAME)[0]
    dc_service = dcs_service.data_center_service(dc.id)
    attached_sds_service = dc_service.storage_domains_service()
    attached_sds_service.add(
        sdk4.types.StorageDomain(
            id=sd.id,
        ),
    )

    attached_sd_service = attached_sds_service.storage_domain_service(sd.id)
    testlib.assert_true_within_long(
        lambda: attached_sd_service.get().status ==
        sdk4.types.StorageDomainStatus.ACTIVE
    )


@testlib.with_ovirt_prefix
def add_master_storage_domain(prefix):
    if MASTER_SD_TYPE == 'iscsi':
        add_iscsi_storage_domain(prefix)
    else:
        add_nfs_storage_domain(prefix)


def add_nfs_storage_domain(prefix):
    if API_V4:
        add_generic_nfs_storage_domain(prefix, SD_NFS_NAME, SD_NFS_HOST_NAME,
                                       SD_NFS_PATH, nfs_version='v4_2')
    else:
        add_generic_nfs_storage_domain(prefix, SD_NFS_NAME, SD_NFS_HOST_NAME,
                                       SD_NFS_PATH, nfs_version='v4_1')


# TODO: add this over the storage network and with IPv6
def add_second_nfs_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_SECOND_NFS_NAME,
                                   SD_NFS_HOST_NAME, SD_SECOND_NFS_PATH)


def add_generic_nfs_storage_domain(prefix, sd_nfs_name, nfs_host_name,
                                   mount_path, sd_format=SD_FORMAT,
                                   sd_type='data', nfs_version='v4_1'):
    if API_V4:
        add_generic_nfs_storage_domain_4(prefix, sd_nfs_name, nfs_host_name,
                                         mount_path, sd_format, sd_type,
                                         nfs_version)
    else:
        add_generic_nfs_storage_domain_3(prefix, sd_nfs_name, nfs_host_name,
                                         mount_path, sd_format, sd_type,
                                         nfs_version)


def add_generic_nfs_storage_domain_3(prefix, sd_nfs_name, nfs_host_name,
                                     mount_path, sd_format=SD_FORMAT,
                                     sd_type='data', nfs_version='v4_1'):
    api = prefix.virt_env.engine_vm().get_api()
    p = params.StorageDomain(
        name=sd_nfs_name,
        data_center=params.DataCenter(
            name=DC_NAME,
        ),
        type_=sd_type,
        storage_format=sd_format,
        host=_random_host_from_dc(api, DC_NAME),
        storage=params.Storage(
            type_='nfs',
            address=_get_host_ip(prefix, nfs_host_name),
            path=mount_path,
            nfs_version=nfs_version,
        ),
    )
    _add_storage_domain_3(api, p)


def add_generic_nfs_storage_domain_4(prefix, sd_nfs_name, nfs_host_name,
                                     mount_path, sd_format='v4',
                                     sd_type='data', nfs_version='v4_2'):
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

    api = prefix.virt_env.engine_vm().get_api(api_ver=4)
    p = sdk4.types.StorageDomain(
        name=sd_nfs_name,
        description='APIv4 NFS storage domain',
        type=dom_type,
        host=_random_host_from_dc_4(api, DC_NAME),
        storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.NFS,
            address=_get_host_ip(prefix, nfs_host_name),
            path=mount_path,
            nfs_version=nfs_vers,
        ),
    )

    _add_storage_domain_4(api, p)


def add_iscsi_storage_domain(prefix):
    # FIXME
    # if API_V4:
    #    return add_iscsi_storage_domain_4(prefix)

    api = prefix.virt_env.engine_vm().get_api()

    # Find LUN GUIDs
    sd_iscsi_host = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME)
    ret = sd_iscsi_host.ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)

    lun_guids = ret.out.splitlines()[:SD_ISCSI_NR_LUNS]

    p = params.StorageDomain(
        name=SD_ISCSI_NAME,
        data_center=params.DataCenter(
            name=DC_NAME,
        ),
        type_='data',
        storage_format='v3',
        host=_random_host_from_dc(api, DC_NAME),
        storage=params.Storage(
            type_='iscsi',
            volume_group=params.VolumeGroup(
                logical_unit=[
                    params.LogicalUnit(
                        id=lun_id,
                        address=_get_host_ip(
                            prefix,
                            SD_ISCSI_HOST_NAME,
                        ),
                        port=SD_ISCSI_PORT,
                        target=SD_ISCSI_TARGET,
                        username='username',
                        password='password',
                    ) for lun_id in lun_guids
                ]

            ),
        ),
    )
    _add_storage_domain_3(api, p)


def add_iso_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_ISO_NAME, SD_ISO_HOST_NAME,
                                   SD_ISO_PATH, sd_format='v1', sd_type='iso',
                                   nfs_version='v3')


def add_templates_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_TEMPLATES_NAME,
                                   SD_TEMPLATES_HOST_NAME, SD_TEMPLATES_PATH,
                                   sd_format='v1', sd_type='export',
                                   nfs_version='v4_1')


_TEST_LIST = [
    add_dc,
    add_cluster,
    add_hosts,
    add_master_storage_domain
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
