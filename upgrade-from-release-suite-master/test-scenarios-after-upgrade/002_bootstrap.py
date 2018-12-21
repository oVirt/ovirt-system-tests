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
import test_utils
from test_utils import network_utils_v4
from test_utils import constants
from test_utils import versioning

# DC/Cluster
DC_NAME = 'test-dc'
DC_VER_MAJ, DC_VER_MIN = [4, 1]
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


def _get_host_ips_in_net(prefix, host_name, net_name):
    return prefix.virt_env.get_vm(host_name).ips_in_net(net_name)

def _hosts_in_dc(api, dc_name=DC_NAME, random_host=False):
    hosts_service = api.system_service().hosts_service()
    hosts = hosts_service.list(search='datacenter={} AND status=up'.format(dc_name))
    if hosts:
        if random_host:
            return random.choice(hosts)
        else:
            return sorted(hosts, key=lambda host: host.name)
    raise RuntimeError('Could not find hosts that are up in DC %s' % dc_name)

def _random_host_from_dc(api, dc_name=DC_NAME):
    return _hosts_in_dc(api, dc_name, True)

def _random_host_service_from_dc(api, dc_name=DC_NAME):
    host = _hosts_in_dc(api, dc_name, True)
    return api.system_service().hosts_service().host_service(id=host.id)


def _single_host_up(hosts_service, total_num_hosts):
    installing_hosts = hosts_service.list(search='datacenter={} AND status=installing or status=initializing'.format(DC_NAME))
    if len(installing_hosts) == total_num_hosts: # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(DC_NAME))
    if len(up_hosts):
        return True

    _check_problematic_hosts(hosts_service)

def _check_problematic_hosts(hosts_service):
    problematic_hosts = hosts_service.list(search='datacenter={} AND status=nonoperational or status=installfailed'.format(DC_NAME))
    if len(problematic_hosts):
        dump_hosts = '%s hosts failed installation:\n' % len(problematic_hosts)
        for host in problematic_hosts:
            host_service = hosts_service.host_service(host.id)
            dump_hosts += '%s: %s\n' % (host.name, host_service.get().status)
        raise RuntimeError(dump_hosts)

@testlib.with_ovirt_api4
def add_dc(api):
    engine = api.system_service()
    dcs_service = engine.data_centers_service()
    with test_utils.TestEvent(engine, 950): # USER_ADD_STORAGE_POOL
        nt.assert_true(
            dcs_service.add(
                sdk4.types.DataCenter(
                    name=DC_NAME,
                    description='APIv4 DC',
                    local=False,
                    version=sdk4.types.Version(major=DC_VER_MAJ,minor=DC_VER_MIN),
                ),
            )
        )


@testlib.with_ovirt_api4
def add_cluster(api):
    engine = api.system_service()
    clusters_service = engine.clusters_service()
    provider_id = network_utils_v4.get_default_ovn_provider_id(engine)
    with test_utils.TestEvent(engine, 809):
        nt.assert_true(
            clusters_service.add(
                sdk4.types.Cluster(
                    name=CLUSTER_NAME,
                    description='APIv4 Cluster',
                    data_center=sdk4.types.DataCenter(
                        name=DC_NAME,
                    ),
                    version=sdk4.types.Version(
                        major=DC_VER_MAJ,
                        minor=DC_VER_MIN
                    ),
                    ballooning_enabled=True,
                    ksm=sdk4.types.Ksm(
                        enabled=True,
                        merge_across_nodes=False,
                    ),
                    scheduling_policy=sdk4.types.SchedulingPolicy(
                        name='evenly_distributed',
                    ),
                    optional_reason=True,
                    memory_policy=sdk4.types.MemoryPolicy(
                        ballooning=True,
                        over_commit=sdk4.types.MemoryOverCommit(
                            percent=150,
                        ),
                    ),
                    ha_reservation=True,
                    external_network_providers=[
                        sdk4.types.ExternalProvider(
                            id=provider_id,
                        )
                    ],
                ),
            )
        )


@testlib.with_ovirt_prefix
def add_hosts(prefix):
    hosts = prefix.virt_env.host_vms()
    api = prefix.virt_env.engine_vm().get_api_v4()
    engine = api.system_service()
    hosts_service = engine.hosts_service()

    def _add_host(vm):
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

    with test_utils.TestEvent(engine, 42):
        for host in hosts:
            nt.assert_true(
                _add_host(host)
            )

@testlib.with_ovirt_api4
def verify_add_hosts(api):
    hosts_service = api.system_service().hosts_service()
    total_hosts = len(hosts_service.list(search='datacenter={}'.format(DC_NAME)))

    testlib.assert_true_within(
        lambda: _single_host_up(hosts_service, total_hosts),
        timeout=constants.ADD_HOST_TIMEOUT
    )


def _add_storage_domain(api, p):
    system_service = api.system_service()
    sds_service = system_service.storage_domains_service()
    with test_utils.TestEvent(system_service, 956): # USER_ADD_STORAGE_DOMAIN(956)
        sd = sds_service.add(p)

        sd_service = sds_service.storage_domain_service(sd.id)
        testlib.assert_true_within_long(
            lambda: sd_service.get().status == sdk4.types.StorageDomainStatus.UNATTACHED
        )

    dc_service = test_utils.data_center_service(system_service, DC_NAME)
    attached_sds_service = dc_service.storage_domains_service()

    with test_utils.TestEvent(system_service, [966, 962]):
        # USER_ACTIVATED_STORAGE_DOMAIN(966)
        # USER_ATTACH_STORAGE_DOMAIN_TO_POOL(962)
        attached_sds_service.add(
            sdk4.types.StorageDomain(
                id=sd.id,
            ),
        )
        attached_sd_service = attached_sds_service.storage_domain_service(sd.id)
        testlib.assert_true_within_long(
            lambda: attached_sd_service.get().status == sdk4.types.StorageDomainStatus.ACTIVE
        )

@testlib.with_ovirt_prefix
def add_master_storage_domain(prefix):
    if MASTER_SD_TYPE == 'iscsi':
        add_iscsi_storage_domain(prefix)
    else:
        add_nfs_storage_domain(prefix)


def add_nfs_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_NFS_NAME, SD_NFS_HOST_NAME, SD_NFS_PATH, nfs_version='v4_2')

def add_generic_nfs_storage_domain(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format='v4', sd_type='data', nfs_version='v4_2'):
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
    ips = _get_host_ips_in_net(prefix, nfs_host_name, testlib.get_prefixed_name('net-storage'))
    kwargs = {}
    if sd_format >= 'v4' and \
       not versioning.cluster_version_ok(4, 1):
        kwargs['storage_format'] = sdk4.types.StorageFormat.V3
    p = sdk4.types.StorageDomain(
        name=sd_nfs_name,
        description='APIv4 NFS storage domain',
        type=dom_type,
        host=_random_host_from_dc(api, DC_NAME),
        storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.NFS,
            address=ips[0],
            path=mount_path,
            nfs_version=nfs_vers,
        ),
        **kwargs
    )

    _add_storage_domain(api, p)

def add_iscsi_storage_domain(prefix):
    luns = test_utils.get_luns(
        prefix, SD_ISCSI_HOST_NAME, SD_ISCSI_PORT, SD_ISCSI_TARGET, from_lun=0, to_lun=SD_ISCSI_NR_LUNS)

    v4_domain = versioning.cluster_version_ok(DC_VER_MAJ, DC_VER_MIN)
    api = prefix.virt_env.engine_vm().get_api_v4()
    p = sdk4.types.StorageDomain(
        name=SD_ISCSI_NAME,
        description='iSCSI Storage Domain',
        type=sdk4.types.StorageDomainType.DATA,
        discard_after_delete=v4_domain,
        data_center=sdk4.types.DataCenter(
            name=DC_NAME,
        ),
        host=_random_host_from_dc(api, DC_NAME),
        storage_format=(sdk4.types.StorageFormat.V4 if v4_domain else sdk4.types.StorageFormat.V3),
        storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.ISCSI,
            override_luns=True,
            volume_group=sdk4.types.VolumeGroup(
                logical_units=luns
            ),
        ),
    )

    _add_storage_domain(api, p)

_TEST_LIST = [
    add_dc,
    add_cluster,
    add_hosts,
    verify_add_hosts,
    add_master_storage_domain
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
