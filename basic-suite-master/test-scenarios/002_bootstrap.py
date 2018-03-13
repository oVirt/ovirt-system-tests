# -*- coding: utf-8 -*-
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
import functools
import httplib
import os
import random
import ssl

import nose.tools as nt
from nose import SkipTest
from ovirtsdk.infrastructure import errors
from ovirtsdk.xml import params

# TODO: import individual SDKv4 types directly (but don't forget sdk4.Error)
import ovirtsdk4 as sdk4

from lago import utils
from ovirtlago import testlib

import test_utils
from test_utils import network_utils_v4
from test_utils import constants
from test_utils import versioning


# TODO: use SDKv4 unconditionally, where possible (as in other test scenarios)
API_V3_ONLY = os.getenv('API_V3_ONLY', False)
if API_V3_ONLY:
    API_V4 = False
else:
    API_V4 = True


MB = 2 ** 20
GB = 2 ** 30

# DC/Cluster
DC_NAME = 'test-dc'
DC_VER_MAJ, DC_VER_MIN = versioning.cluster_version()
SD_FORMAT = 'v4'
CLUSTER_NAME = 'test-cluster'
DC_QUOTA_NAME = 'DC-QUOTA'
TEMPLATE_BLANK = 'Blank'

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
CIRROS_IMAGE_NAME = 'CirrOS 0.4.0 for x86_64'
GLANCE_DISK_NAME = CIRROS_IMAGE_NAME.replace(" ", "_") + '_glance_disk'
TEMPLATE_CIRROS = CIRROS_IMAGE_NAME.replace(" ", "_") + '_glance_template'
GLANCE_SERVER_URL = 'http://glance.ovirt.org:9292/'

# Network
VM_NETWORK = u'VM Network with a very long name and עברית'
VM_NETWORK_VLAN_ID = 100
MIGRATION_NETWORK = 'Migration_Net'
MANAGEMENT_NETWORK = 'ovirtmgmt'
PASSTHROUGH_VNIC_PROFILE = 'passthrough_vnic_profile'
NETWORK_FILTER_NAME = 'clean-traffic'
NETWORK_FILTER_PARAMETER0_NAME = 'CTRL_IP_LEARNING'
NETWORK_FILTER_PARAMETER0_VALUE = 'dhcp'
NETWORK_FILTER_PARAMETER1_NAME = 'DHCPSERVER'


VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
VM2_NAME = 'vm2'
BACKUP_VM_NAME = 'backup_vm'

# the default MAC pool has addresses like 00:1a:4a:16:01:51
UNICAST_MAC_OUTSIDE_POOL = '0a:1a:4a:16:01:51'


# TODO: support resolving hosts over IPv6 and arbitrary network
def _get_host_ip(prefix, host_name):
    return prefix.virt_env.get_vm(host_name).ip()

def _get_host_all_ips(prefix, host_name):
    return prefix.virt_env.get_vm(host_name).all_ips()

def _get_host_ips_in_net(prefix, host_name, net_name):
    return prefix.virt_env.get_vm(host_name).ips_in_net(net_name)

def _hosts_in_dc(api, dc_name=DC_NAME):
    hosts = api.hosts.list(query='datacenter={} AND status=up'.format(dc_name))
    if hosts:
        return sorted(hosts, key=lambda host: host.name)
    raise RuntimeError('Could not find hosts that are up in DC %s' % dc_name)

def _hosts_in_dc_4(api, dc_name=DC_NAME, random_host=False):
    hosts_service = api.system_service().hosts_service()
    hosts = hosts_service.list(search='datacenter={} AND status=up'.format(dc_name))
    if hosts:
        if random_host:
            return random.choice(hosts)
        else:
            return sorted(hosts, key=lambda host: host.name)
    raise RuntimeError('Could not find hosts that are up in DC %s' % dc_name)

def _random_host_from_dc(api, dc_name=DC_NAME):
    return random.choice(_hosts_in_dc(api, dc_name))

def _random_host_from_dc_4(api, dc_name=DC_NAME):
    return _hosts_in_dc_4(api, dc_name, True)

def _all_hosts_up(hosts_service, total_hosts):
    installing_hosts = hosts_service.list(search='datacenter={} AND status=installing or status=initializing'.format(DC_NAME))
    if len(installing_hosts) == len(total_hosts): # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(DC_NAME))
    if len(up_hosts) == len(total_hosts):
        return True

    _check_problematic_hosts(hosts_service)

def _single_host_up(hosts_service, total_hosts):
    installing_hosts = hosts_service.list(search='datacenter={} AND status=installing or status=initializing'.format(DC_NAME))
    if len(installing_hosts) == len(total_hosts): # All hosts still installing
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


@testlib.with_ovirt_prefix
def add_dc(prefix):
    if API_V4:
        api = prefix.virt_env.engine_vm().get_api(api_ver=4)
        add_dc_4(api)
    else:
        api = prefix.virt_env.engine_vm().get_api()
        add_dc_3(api)


def add_dc_3(api):
    p = params.DataCenter(
        name=DC_NAME,
        local=False,
        version=params.Version(
            major=DC_VER_MAJ,
            minor=DC_VER_MIN,
        ),
    )
    nt.assert_true(api.datacenters.add(p))


def add_dc_4(api):
    dcs_service = api.system_service().data_centers_service()
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


@testlib.with_ovirt_prefix
def remove_default_dc(prefix):
    if API_V4:
        api = prefix.virt_env.engine_vm().get_api(api_ver=4)
        remove_default_dc_4(api)
    else:
        api = prefix.virt_env.engine_vm().get_api()
        remove_default_dc_3(api)


def remove_default_dc_3(api):
    nt.assert_true(api.datacenters.get(name='Default').delete())


def remove_default_dc_4(api):
    dc_service = test_utils.data_center_service(api.system_service(), 'Default')
    dc_service.remove()


@testlib.with_ovirt_api4
def update_default_dc(api):
    dc_service = test_utils.data_center_service(api.system_service(), 'Default')
    dc_service.update(
        data_center=sdk4.types.DataCenter(
            local=True
        )
    )


@testlib.with_ovirt_api4
def update_default_cluster(api):
    cluster_service = test_utils.get_cluster_service(api.system_service(), 'Default')
    cluster_service.update(
        cluster=sdk4.types.Cluster(
            cpu=sdk4.types.Cpu(
                architecture=sdk4.types.Architecture.PPC64
            )
        )
    )


@testlib.with_ovirt_prefix
def remove_default_cluster(prefix):
    if API_V4:
        api = prefix.virt_env.engine_vm().get_api(api_ver=4)
        remove_default_cluster_4(api)
    else:
        api = prefix.virt_env.engine_vm().get_api()
        remove_default_cluster_3(api)


def remove_default_cluster_3(api):
    nt.assert_true(api.clusters.get(name='Default').delete())


def remove_default_cluster_4(api):
    cl_service = test_utils.get_cluster_service(api.system_service(), 'Default')
    cl_service.remove()


@testlib.with_ovirt_prefix
def add_dc_quota(prefix):
    if API_V4:
#FIXME - add API_v4 add_dc_quota_4() function
        api = prefix.virt_env.engine_vm().get_api()
        add_dc_quota_3(api)
    else:
        api = prefix.virt_env.engine_vm().get_api()
        add_dc_quota_3(api)


def add_dc_quota_3(api):
        dc = api.datacenters.get(name=DC_NAME)
        quota = params.Quota(
            name=DC_QUOTA_NAME,
            description='DC-QUOTA-DESCRIPTION',
            data_center=dc,
            cluster_soft_limit_pct=99,
        )
        nt.assert_true(dc.quotas.add(quota))


@testlib.with_ovirt_prefix
def add_cluster(prefix):
    if API_V4:
        add_cluster_4(prefix)
    else:
        add_cluster_3(prefix)


def add_cluster_3(prefix):
    api = prefix.virt_env.engine_vm().get_api()
    p = params.Cluster(
        name=CLUSTER_NAME,
        version=params.Version(
            major=DC_VER_MAJ,
            minor=DC_VER_MIN,
        ),
        data_center=params.DataCenter(
            name=DC_NAME,
        ),
        ballooning_enabled=True,
    )
    nt.assert_true(api.clusters.add(p))


def add_cluster_4(prefix):
    api = prefix.virt_env.engine_vm().get_api(api_ver=4)
    engine = api.system_service()
    clusters_service = engine.clusters_service()
    provider_id = network_utils_v4.get_default_ovn_provider_id(engine)
    nt.assert_true(
        clusters_service.add(
            sdk4.types.Cluster(
                name=CLUSTER_NAME,
                description='APIv4 Cluster',
                data_center=sdk4.types.DataCenter(
                    name=DC_NAME,
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
    for host in hosts:
        host.ssh(['ntpdate', '-4', testlib.get_prefixed_name('engine')])

    if API_V4:
        api = prefix.virt_env.engine_vm().get_api_v4()
        add_hosts_4(api, hosts)
    else:
        api = prefix.virt_env.engine_vm().get_api()
        add_hosts_3(api, hosts)


@testlib.with_ovirt_prefix
def verify_add_hosts(prefix):
    hosts = prefix.virt_env.host_vms()

    if API_V4:
        api = prefix.virt_env.engine_vm().get_api_v4()
        verify_add_hosts_4(api)
    else:
        api = prefix.virt_env.engine_vm().get_api()
        verify_add_hosts_3(api, hosts)
        for host in hosts:
            host.ssh(['rm', '-rf', '/dev/shm/yum', '/dev/shm/*.rpm'])



def add_hosts_3(api, hosts):
    def _add_host(vm):
        p = params.Host(
            name=vm.name(),
            address=vm.ip(),
            cluster=params.Cluster(
                name=CLUSTER_NAME,
            ),
            root_password=vm.root_password(),
            override_iptables=True,
        )

        return api.hosts.add(p)

    vec = utils.func_vector(_add_host, [(h,) for h in hosts])
    vt = utils.VectorThread(vec)
    vt.start_all()
    nt.assert_true(all(vt.join_all()))


def verify_add_hosts_3(api, hosts):
    def _host_is_up():
        cur_state = api.hosts.get(host.name()).status.state

        if cur_state == 'up':
            return True

        if cur_state == 'install_failed':
            raise RuntimeError('Host %s failed to install' % host.name())
        if cur_state == 'non_operational':
            raise RuntimeError('Host %s is in non operational state' % host.name())

    for host in hosts:
        testlib.assert_true_within(_host_is_up, timeout=constants.ADD_HOST_TIMEOUT)


def add_hosts_4(api, hosts):
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

    for host in hosts:
        nt.assert_true(
            _add_host_4(host)
        )


def verify_add_hosts_4(api):
    hosts_service = api.system_service().hosts_service()
    total_hosts = hosts_service.list(search='datacenter={}'.format(DC_NAME))

    testlib.assert_true_within(
        lambda: _single_host_up(hosts_service, total_hosts),
        timeout=constants.ADD_HOST_TIMEOUT
    )

@testlib.with_ovirt_prefix
def verify_add_all_hosts(prefix):
    api = prefix.virt_env.engine_vm().get_api_v4()
    hosts_service = api.system_service().hosts_service()
    total_hosts = hosts_service.list(search='datacenter={}'.format(DC_NAME))

    testlib.assert_true_within(
        lambda: _all_hosts_up(hosts_service, total_hosts),
        timeout=constants.ADD_HOST_TIMEOUT
    )

    hosts = prefix.virt_env.host_vms()
    for host in hosts:
        host.ssh(['rm', '-rf', '/dev/shm/yum', '/dev/shm/*.rpm'])


@testlib.with_ovirt_prefix
def copy_storage_script(prefix):
    engine = prefix.virt_env.engine_vm()
    storage_script = os.path.join(
        os.environ.get('SUITE'), 'setup_storage.sh'
    )
    engine.copy_to(
        storage_script,
        '/tmp/setup_storage.sh',
    )


@testlib.with_ovirt_prefix
def configure_storage(prefix):
    engine = prefix.virt_env.engine_vm()
    result = engine.ssh(
        [
            '/tmp/setup_storage.sh',
        ],
    )
    nt.eq_(
        result.code, 0, 'setup_storage.sh failed. Exit code is %s' % result.code
    )


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
    system_service = api.system_service()
    sds_service = system_service.storage_domains_service()
    sd = sds_service.add(p)

    sd_service = sds_service.storage_domain_service(sd.id)
    testlib.assert_true_within_long(
        lambda: sd_service.get().status == sdk4.types.StorageDomainStatus.UNATTACHED
    )

    dc_service = test_utils.data_center_service(system_service, DC_NAME)
    attached_sds_service = dc_service.storage_domains_service()
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
    if API_V4:
        add_generic_nfs_storage_domain(prefix, SD_NFS_NAME, SD_NFS_HOST_NAME, SD_NFS_PATH, nfs_version='v4_2')
    else:
        add_generic_nfs_storage_domain(prefix, SD_NFS_NAME, SD_NFS_HOST_NAME, SD_NFS_PATH, nfs_version='v4_1')


# TODO: add this over the storage network and with IPv6
def add_second_nfs_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_SECOND_NFS_NAME,
                                   SD_NFS_HOST_NAME, SD_SECOND_NFS_PATH)


def add_generic_nfs_storage_domain(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format=SD_FORMAT, sd_type='data', nfs_version='v4_1'):
    if API_V4:
        add_generic_nfs_storage_domain_4(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format, sd_type, nfs_version)
    else:
        add_generic_nfs_storage_domain_3(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format, sd_type, nfs_version)


def add_generic_nfs_storage_domain_3(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format=SD_FORMAT, sd_type='data', nfs_version='v4_1'):
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


def add_generic_nfs_storage_domain_4(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format='v4', sd_type='data', nfs_version='v4_2'):
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
    p = sdk4.types.StorageDomain(
        name=sd_nfs_name,
        description='APIv4 NFS storage domain',
        type=dom_type,
        host=_random_host_from_dc_4(api, DC_NAME),
        storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.NFS,
            address=ips[0],
            path=mount_path,
            nfs_version=nfs_vers,
        ),
    )

    _add_storage_domain_4(api, p)

@testlib.with_ovirt_prefix
def add_secondary_storage_domains(prefix):
    if MASTER_SD_TYPE == 'iscsi':
        vt = utils.VectorThread(
            [
                functools.partial(add_nfs_storage_domain, prefix),
# 12/07/2017 commenting out iso domain creation until we know why it causing random failures
# Bug-Url: http://bugzilla.redhat.com/1463263
#                functools.partial(add_iso_storage_domain, prefix),
                functools.partial(add_templates_storage_domain, prefix),
                functools.partial(add_second_nfs_storage_domain, prefix),

            ],
        )
    else:
        vt = utils.VectorThread(
            [
                functools.partial(add_iscsi_storage_domain, prefix),
# 12/07/2017 commenting out iso domain creation until we know why it causing random failures
#Bug-Url: http://bugzilla.redhat.com/1463263
#                functools.partial(add_iso_storage_domain, prefix),
                functools.partial(add_templates_storage_domain, prefix),
                functools.partial(add_second_nfs_storage_domain, prefix),

            ],
        )
    vt.start_all()
    vt.join_all()


@testlib.with_ovirt_prefix
def add_glance_images(prefix):
    api = prefix.virt_env.engine_vm().get_api()
    glance_provider = api.storagedomains.get(SD_GLANCE_NAME)

    vt = utils.VectorThread(
        [
            functools.partial(import_non_template_from_glance, glance_provider),
            functools.partial(import_template_from_glance, glance_provider),
        ],
    )
    vt.start_all()
    vt.join_all()


def add_iscsi_storage_domain(prefix):
    ret = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)
    lun_guids = ret.out.splitlines()[0:SD_ISCSI_NR_LUNS-1]

    if API_V4:
        add_iscsi_storage_domain_4(prefix, lun_guids)
    else:
        add_iscsi_storage_domain_3(prefix, lun_guids)


def add_iscsi_storage_domain_3(prefix, lun_guids):
    api = prefix.virt_env.engine_vm().get_api()

    ips = _get_host_all_ips(prefix, SD_ISCSI_HOST_NAME)
    luns = []
    for lun_id in lun_guids:
        for ip in ips:
            lun=params.LogicalUnit(
                id=lun_id,
                address=ip,
                port=SD_ISCSI_PORT,
                target=SD_ISCSI_TARGET,
                username='username',
                password='password',
            )
            luns.append(lun)

    p = params.StorageDomain(
        name=SD_ISCSI_NAME,
        data_center=params.DataCenter(
            name=DC_NAME,
        ),
        type_='data',
        storage_format=SD_FORMAT,
        host=_random_host_from_dc(api, DC_NAME),
        storage=params.Storage(
            type_='iscsi',
            volume_group=params.VolumeGroup(
                logical_unit=luns
            ),
        ),
    )
    _add_storage_domain_3(api, p)


def add_iscsi_storage_domain_4(prefix, lun_guids):
    api = prefix.virt_env.engine_vm().get_api_v4()

    ips = _get_host_all_ips(prefix, SD_ISCSI_HOST_NAME)
    luns = []
    for lun_id in lun_guids:
        for ip in ips:
            lun=sdk4.types.LogicalUnit(
                id=lun_id,
                address=ip,
                port=SD_ISCSI_PORT,
                target=SD_ISCSI_TARGET,
                username='username',
                password='password',
            )
            luns.append(lun)

    p = sdk4.types.StorageDomain(
        name=SD_ISCSI_NAME,
        description='iSCSI Storage Domain',
        type=sdk4.types.StorageDomainType.DATA,
        discard_after_delete=True,
        data_center=sdk4.types.DataCenter(
            name=DC_NAME,
        ),
        host=_random_host_from_dc_4(api, DC_NAME),
        storage_format=sdk4.types.StorageFormat.V4,
        storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.ISCSI,
            override_luns=True,
            volume_group=sdk4.types.VolumeGroup(
                logical_units=luns
            ),
        ),
    )

    _add_storage_domain_4(api, p)


def add_iso_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_ISO_NAME, SD_ISO_HOST_NAME, SD_ISO_PATH, sd_format='v1', sd_type='iso', nfs_version='v3')


def add_templates_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_TEMPLATES_NAME, SD_TEMPLATES_HOST_NAME, SD_TEMPLATES_PATH, sd_format='v1', sd_type='export', nfs_version='v4_1')


@testlib.with_ovirt_api
def import_templates(api):
    #TODO: Fix the exported domain generation
    raise SkipTest('Exported domain generation not supported yet')
    templates = api.storagedomains.get(
        SD_TEMPLATES_NAME,
    ).templates.list(
        unregistered=True,
    )

    for template in templates:
        template.register(
            action=params.Action(
                cluster=params.Cluster(
                    name=CLUSTER_NAME,
                ),
            ),
        )

    for template in api.templates.list():
        testlib.assert_true_within_short(
            lambda: api.templates.get(template.name).status.state == 'ok',
        )


def generic_import_from_glance(glance_provider, image_name=CIRROS_IMAGE_NAME, as_template=False, image_ext='_glance_disk', template_ext='_glance_template', dest_storage_domain=MASTER_SD_TYPE, dest_cluster=CLUSTER_NAME):
    target_image = glance_provider.images.get(name=image_name)
    disk_name = image_name.replace(" ", "_") + image_ext
    template_name = image_name.replace(" ", "_") + template_ext
    import_action = params.Action(
        storage_domain=params.StorageDomain(
            name=dest_storage_domain,
        ),
        cluster=params.Cluster(
            name=dest_cluster,
        ),
        import_as_template=as_template,
        disk=params.Disk(
            name=disk_name,
        ),
        template=params.Template(
            name=template_name,
        ),
    )

    nt.assert_true(
        target_image.import_image(import_action)
    )


@testlib.with_ovirt_prefix
def list_glance_images(prefix):
    if API_V4:
        api = prefix.virt_env.engine_vm().get_api(api_ver=4)
        list_glance_images_4(api)
    else:
        api = prefix.virt_env.engine_vm().get_api()
        list_glance_images_3(api)


def list_glance_images_3(api):
    global GLANCE_AVAIL
    glance_provider = api.storagedomains.get(SD_GLANCE_NAME)
    if glance_provider is None:
        openstack_glance = add_glance_3(api)
        if openstack_glance is None:
            raise SkipTest('%s: GLANCE storage domain is not available.' % list_glance_images_3.__name__ )
        glance_provider = api.storagedomains.get(SD_GLANCE_NAME)

    if not check_glance_connectivity_3(api):
        raise SkipTest('%s: GLANCE connectivity test failed' % list_glance_images_3.__name__ )

    try:
        all_images = glance_provider.images.list()
        if len(all_images):
            GLANCE_AVAIL = True
    except errors.RequestError:
        raise SkipTest('%s: GLANCE is not available: client request error' % list_glance_images_3.__name__ )


def list_glance_images_4(api):
    global GLANCE_AVAIL
    search_query = 'name={}'.format(SD_GLANCE_NAME)
    storage_domains_service = api.system_service().storage_domains_service()
    glance_domain_list = storage_domains_service.list(search=search_query)

    if not glance_domain_list:
        openstack_glance = add_glance_4(api)
        if not openstack_glance:
            raise SkipTest('%s GLANCE storage domain is not available.' % list_glance_images_4.__name__ )
        glance_domain_list = storage_domains_service.list(search=search_query)

    if not check_glance_connectivity_4(api):
        raise SkipTest('%s: GLANCE connectivity test failed' % list_glance_images_4.__name__ )

    glance_domain = glance_domain_list.pop()
    glance_domain_service = storage_domains_service.storage_domain_service(glance_domain.id)

    try:
        all_images = glance_domain_service.images_service().list()
        if len(all_images):
            GLANCE_AVAIL = True
    except sdk4.Error:
        raise SkipTest('%s: GLANCE is not available: client request error' % list_glance_images_4.__name__ )


def add_glance_3(api):
    target_server = params.OpenStackImageProvider(
        name=SD_GLANCE_NAME,
        url=GLANCE_SERVER_URL
    )
    try:
        provider = api.openstackimageproviders.add(target_server)
        glance = []

        def get():
            instance = api.openstackimageproviders.get(id=provider.get_id())
            if instance:
                glance.append(instance)
                return True
            else:
                return False

        testlib.assert_true_within_short(func=get, allowed_exceptions=[errors.RequestError])
    except (AssertionError, errors.RequestError):
        # RequestError if add method was failed.
        # AssertionError if add method succeed but we couldn't verify that glance was actually added
        return None

    return glance.pop()


def add_glance_4(api):
    target_server = sdk4.types.OpenStackImageProvider(
        name=SD_GLANCE_NAME,
        description=SD_GLANCE_NAME,
        url=GLANCE_SERVER_URL,
        requires_authentication=False
    )

    try:
        providers_service = api.system_service().openstack_image_providers_service()
        providers_service.add(target_server)
        glance = []

        def get():
            providers = [
                provider for provider in providers_service.list()
                if provider.name == SD_GLANCE_NAME
            ]
            if not providers:
                return False
            instance = providers_service.provider_service(providers.pop().id)
            if instance:
                glance.append(instance)
                return True
            else:
                return False

        testlib.assert_true_within_short(func=get, allowed_exceptions=[errors.RequestError])
    except (AssertionError, errors.RequestError):
        # RequestError if add method was failed.
        # AssertionError if add method succeed but we couldn't verify that glance was actually added
        return None

    return glance.pop()


def check_glance_connectivity_3(api):
    avail = False
    try:
        glance = api.openstackimageproviders.get(name=SD_GLANCE_NAME)
        glance.testconnectivity()
        avail = True
    except errors.RequestError:
        pass

    return avail


def check_glance_connectivity_4(api):
    avail = False
    providers_service = api.system_service().openstack_image_providers_service()
    providers = [
        provider for provider in providers_service.list()
        if provider.name == SD_GLANCE_NAME
    ]
    if providers:
        glance = providers_service.provider_service(providers.pop().id)
        try:
            glance.test_connectivity()
            avail = True
        except sdk4.Error:
            pass

    return avail


def import_non_template_from_glance(glance_provider):
    if not GLANCE_AVAIL:
        raise SkipTest('%s: GLANCE is not available.' % import_non_template_from_glance.__name__ )
    generic_import_from_glance(glance_provider)


def import_template_from_glance(glance_provider):
    if not GLANCE_AVAIL:
        raise SkipTest('%s: GLANCE is not available.' % import_template_from_glance.__name__ )
    generic_import_from_glance(glance_provider, image_name=CIRROS_IMAGE_NAME, image_ext='_glance_template', as_template=True)


@testlib.with_ovirt_api
def set_dc_quota_audit(api):
    dc = api.datacenters.get(name=DC_NAME)
    dc.set_quota_mode('audit')
    nt.assert_true(
        dc.update()
    )


@testlib.with_ovirt_api
def add_quota_storage_limits(api):
    dc = api.datacenters.get(DC_NAME)
    quota = dc.quotas.get(name=DC_QUOTA_NAME)
    quota_storage = params.QuotaStorageLimit(limit=500)
    nt.assert_true(
        quota.quotastoragelimits.add(quota_storage)
    )


@testlib.with_ovirt_api
def add_quota_cluster_limits(api):
    dc = api.datacenters.get(DC_NAME)
    quota = dc.quotas.get(name=DC_QUOTA_NAME)
    quota_cluster = params.QuotaClusterLimit(vcpu_limit=20, memory_limit=10000)
    nt.assert_true(
        quota.quotaclusterlimits.add(quota_cluster)
    )


@testlib.with_ovirt_api4
def add_vm_network(api):
    engine = api.system_service()

    network = network_utils_v4.create_network_params(
        VM_NETWORK,
        DC_NAME,
        description='VM Network (originally on VLAN {})'.format(
            VM_NETWORK_VLAN_ID),
        vlan=sdk4.types.Vlan(
            id=VM_NETWORK_VLAN_ID,
        ),
    )

    nt.assert_true(
        engine.networks_service().add(network)
    )

    cluster_service = test_utils.get_cluster_service(engine, CLUSTER_NAME)
    nt.assert_true(
        cluster_service.networks_service().add(network)
    )


@testlib.with_ovirt_api4
def add_non_vm_network(api):
    engine = api.system_service()

    network = network_utils_v4.create_network_params(
        MIGRATION_NETWORK,
        DC_NAME,
        description='Non VM Network on VLAN 200, MTU 9000',
        vlan=sdk4.types.Vlan(
            id='200',
        ),
        usages=[],
        mtu=9000,
    )

    nt.assert_true(
        engine.networks_service().add(network)
    )

    cluster_service = test_utils.get_cluster_service(engine, CLUSTER_NAME)
    nt.assert_true(
        cluster_service.networks_service().add(network)
    )


@testlib.with_ovirt_api4
def add_role(api):
    roles_service = api.system_service().roles_service()
    nt.assert_true(
        roles_service.add(
            sdk4.types.Role(
                name='MyRole',
                administrative=False,
                description='My custom role to create virtual machines',
                permits=[
                    # create_vm permit
                    sdk4.types.Permit(id='1'),
                    # login permit
                    sdk4.types.Permit(id='1300'),
                ],
            ),
        )
    )


@testlib.with_ovirt_api4
def add_affinity_label(api):
    affinity_labels_service = api.system_service().affinity_labels_service()
    nt.assert_true(
        affinity_labels_service.add(
            sdk4.types.AffinityLabel(
                name='my_affinity_label',
            ),
        )
    )


@testlib.with_ovirt_api4
def add_affinity_group(api):
    cluster_service = test_utils.get_cluster_service(api.system_service(), CLUSTER_NAME)
    affinity_group_service = cluster_service.affinity_groups_service()
    nt.assert_true(
        affinity_group_service.add(
            sdk4.types.AffinityGroup(
                name='my_affinity_group',
                enforcing=False,
                positive=True,
                hosts_rule=sdk4.types.AffinityRule(
                    enabled=False,
                    enforcing=False,
                    positive=True,
                ),
            ),
        )
    )


@testlib.with_ovirt_api4
def add_bookmark(api):
    bookmarks_service = api.system_service().bookmarks_service()
    nt.assert_true(
        bookmarks_service.add(
            sdk4.types.Bookmark(
                name='my_bookmark',
                value='vm:name=vm*',
            ),
        )
    )


@testlib.with_ovirt_api4
def add_cpu_profile(api):
    cpu_profiles_service = api.system_service().cpu_profiles_service()
    cluster_service = test_utils.get_cluster_service(api.system_service(), CLUSTER_NAME)
    nt.assert_true(
        cpu_profiles_service.add(
            sdk4.types.CpuProfile(
                name='my_cpu_profile',
                cluster=sdk4.types.Cluster(
                    id=cluster_service.get().id,
                ),
            ),
        )
    )


@testlib.with_ovirt_api4
def add_qos(api):
    engine = api.system_service()
    dc_service = test_utils.data_center_service(engine, DC_NAME)
    qoss = dc_service.qoss_service()
    nt.assert_true(
        qoss.add(
            sdk4.types.Qos(
                name='my_cpu_qos',
                type=sdk4.types.QosType.CPU,
                cpu_limit=99,
            ),
        )
    )
    nt.assert_true(
        qoss.add(
            sdk4.types.Qos(
                name='my_storage_qos',
                type=sdk4.types.QosType.STORAGE,
                max_iops=999999,
                description='max_iops_qos',
            ),
        )
    )

@testlib.with_ovirt_api4
def add_disk_profile(api):
    engine = api.system_service()
    disk_profiles_service = engine.disk_profiles_service()
    dc_service = test_utils.data_center_service(engine, DC_NAME)
    attached_sds_service = dc_service.storage_domains_service()
    attached_sd = attached_sds_service.list()[0]

    nt.assert_true(
        disk_profiles_service.add(
            sdk4.types.DiskProfile(
                name='my_disk_profile',
                storage_domain=sdk4.types.StorageDomain(
                    id=attached_sd.id,
                ),
            ),
        )
    )


@testlib.with_ovirt_api4
def get_version(api):
    engine = api.system_service()
    product_info = engine.get().product_info
    name = product_info.name
    major_version = product_info.version.major
    nt.assert_true(
        name == 'oVirt Engine'
    )
    nt.assert_true(
        major_version == 4
    )


@testlib.with_ovirt_api4
def get_cluster_enabled_features(api):
    engine = api.system_service()
    cluster_service = test_utils.get_cluster_service(engine, CLUSTER_NAME)
    enabled_features_service = cluster_service.enabled_features_service()
    features = sorted(enabled_features_service.list(), key=lambda feature: feature.name)
    #TODO: Fix the below - why is features null?
    raise SkipTest('skipping - features is []')
    feature_list = ''
    for feature in features:
        if feature.name == 'XYZ':
            return True
        else:
            feature_list += (feature.name + '; ')
    raise RuntimeError('Feature XYZ is not in cluster enabled features: {0}'.format(feature_list))


@testlib.with_ovirt_api4
def get_cluster_levels(api):
    cluster_levels_service = api.system_service().cluster_levels_service()
    cluster_levels = sorted(cluster_levels_service.list(), key=lambda level:level.id)
    nt.assert_true(cluster_levels)
    levels = ''
    for level in cluster_levels:
        if level.id == '4.2':
            cluster_level_service = cluster_levels_service.level_service(level.id)
            cl42 = cluster_level_service.get()
            #TODO: complete testing for features in 4.2 level.
            return True
        else:
            levels += (level.id + '; ')
    raise RuntimeError('Could not find 4.2 in cluster_levels: {0}'.format(levels))


@testlib.with_ovirt_api4
def get_domains(api):
    domains_service = api.system_service().domains_service()
    domains = sorted(domains_service.list(), key=lambda domain: domain.name)
    for domain in domains:
        if domain.name == 'internal-authz':
            return True
    raise RuntimeError('Could not find internal-authz domain in domains list')


@testlib.with_ovirt_api4
def get_host_devices(api):
    engine = api.system_service()
    host = _random_host_from_dc_4(api, DC_NAME)
    host_service = engine.hosts_service().host_service(id=host.id)
    devices_service = host_service.devices_service()
    devices = sorted(devices_service.list(), key=lambda device: device.name)
    device_list = ''
    for device in devices:
        if device.name == 'block_vda_1': # first virtio-blk disk
            return True
        else:
            device_list += (device.name + '; ')
    raise RuntimeError('Could not find block_vda1 device in host devices: {}'.format(device_list))


@testlib.with_ovirt_api4
def get_host_hooks(api):
    engine = api.system_service()
    host = _random_host_from_dc_4(api, DC_NAME)
    host_service = engine.hosts_service().host_service(id=host.id)
    hooks_service = host_service.hooks_service()
    hooks = sorted(hooks_service.list(), key=lambda hook: hook.name)
    hooks_list = ''
    for hook in hooks:
        if hook.name == '50_vhostmd':
            return True
        else:
            hooks_list += (hook.name + '; ')
    raise RuntimeError('could not find 50_vhostmd hook in host hooks: {0}'.format(hooks_list))


@testlib.with_ovirt_api4
def get_host_stats(api):
    engine = api.system_service()
    host = _random_host_from_dc_4(api, DC_NAME)
    host_service = engine.hosts_service().host_service(id=host.id)
    stats_service = host_service.statistics_service()
    stats = sorted(stats_service.list(), key=lambda stat: stat.name)
    stats_list = ''
    for stat in stats:
        if stat.name == 'boot.time':
            return True
        else:
            stats_list += (stat.name + '; ')
    raise RuntimeError('boot.time stat not in stats: {0}'.format(stats_list))


@testlib.with_ovirt_api4
def get_host_numa_nodes(api):
    engine = api.system_service()
    host = _random_host_from_dc_4(api, DC_NAME)
    host_service = engine.hosts_service().host_service(id=host.id)
    numa_nodes_service = host_service.numa_nodes_service()
    nodes = numa_nodes_service.list()
    # TODO: Do a better check on the result nodes struct.
    # The below is too simplistic.
    raise SkipTest(' [2018-02-08] test itself identified as possibly faulty')
    nt.assert_true(
        nodes[0].index == 0
    )


@testlib.with_ovirt_api4
def check_update_host(api):
    engine = api.system_service()
    host = _random_host_from_dc_4(api, DC_NAME)
    host_service = engine.hosts_service().host_service(id=host.id)
    events_service = engine.events_service()
    last_event = int(events_service.list(max=2)[0].id)
    host_service.upgrade_check()

    # HOST_AVAILABLE_UPDATES_STARTED(884)
    testlib.assert_true_within_short(
        lambda:
        any(e.code == 884 for e in events_service.list(from_=last_event))
    )

    # HOST_AVAILABLE_UPDATES_FINISHED(885)
    last_event = int(events_service.list(max=2)[0].id)
    testlib.assert_true_within_short(
        lambda:
        any(e.code == 885 for e in events_service.list(from_=last_event))
    )


@testlib.with_ovirt_api4
def add_scheduling_policy(api):
    scheduling_policies_service = api.system_service().scheduling_policies_service()
    nt.assert_true(
        scheduling_policies_service.add(
            sdk4.types.SchedulingPolicy(
                name='my_scheduling_policy',
                default_policy=False,
                locked=False,
                balances=[
                    sdk4.types.Balance(
                        name='OptimalForEvenDistribution',
                    ),
                ],
                filters=[
                    sdk4.types.Filter(
                        name='Migration',
                    ),
                ],
                weight=[
                    sdk4.types.Weight(
                        name='HA',
                        factor=2,
                    ),
                ],
            )
        )
    )


@testlib.with_ovirt_api4
def get_system_options(api):
    #TODO: get some option
    options_service = api.system_service().options_service()


@testlib.with_ovirt_api4
def get_operating_systems(api):
    operating_systems_service = api.system_service().operating_systems_service()
    os_list = sorted(operating_systems_service.list(), key=lambda os:os.name)
    nt.assert_true(os_list)
    os_string = ''
    for os in os_list:
        if os.name == 'rhel_7x64':
            return True
        else:
            os_string += (os.name + '; ')
    raise RuntimeError('Could not find rhel_7x64 in operating systems list: {0}'.format(os_string))


@testlib.with_ovirt_api4
def add_fence_agent(api):
    # TODO: This just adds a fence agent to host, does not enable it.
    # Of course, we need to find a fence agents that can work on
    # VMs via the host libvirt, etc...
    engine = api.system_service()
    host = _random_host_from_dc_4(api, DC_NAME)
    host_service = engine.hosts_service().host_service(id=host.id)

    fence_agents_service = host_service.fence_agents_service()
    raise SkipTest('Enabling this may affect tests. Needs further tests')
    nt.assert_true(
        fence_agents_service.add(
            sdk4.types.Agent(
                address='1.2.3.4',
                type='ipmilan',
                username='myusername',
                password='mypassword',
                options=[
                    sdk4.types.Option(
                        name='myname',
                        value='myvalue',
                    ),
                ],
                order=0,
            )
        )
    )


@testlib.with_ovirt_api4
def add_tag(api):
    tags_service = api.system_service().tags_service()
    nt.assert_true(
        tags_service.add(
            sdk4.types.Tag(
                name='mytag',
                description='My custom tag',
            ),
        )
    )


@testlib.with_ovirt_api4
def add_mac_pool(api):
    pools_service = api.system_service().mac_pools_service()
    pool = pools_service.add(
        sdk4.types.MacPool(
            name='mymacpool',
            ranges=[
                sdk4.types.Range(
                    from_='02:00:00:00:00:00',
                    to='02:00:00:01:00:00',
                ),
            ],
        ),
    )
    nt.assert_true(pool)

    cluster_service = test_utils.get_cluster_service(api.system_service(), 'Default')
    nt.assert_true(
        cluster_service.update(
            cluster=sdk4.types.Cluster(
                mac_pool=sdk4.types.MacPool(
                    id=pool.id,
                )
            )
        )
    )


@testlib.with_ovirt_prefix
def verify_notifier(prefix):
    engine = prefix.virt_env.engine_vm()
    result = engine.ssh(
        [
            'grep',
            'VDC_STOP',
            '/var/log/messages',
        ],
    )
    nt.eq_(
        result.code,
        0,
        'Failed grep for VDC_STOP with code {0}. Output: {1}'.format(result.code, result.out)
    )
    engine.service('ovirt-engine-notifier')._request_stop()
    engine.service('snmptrapd')._request_stop()


@testlib.with_ovirt_prefix
def verify_engine_backup(prefix):
    engine = prefix.virt_env.engine_vm()
    engine.ssh(
        [
            'mkdir',
            '/var/log/ost-engine-backup',
        ],
    )
    result = engine.ssh(
        [
            'engine-backup',
            '--mode=backup',
            '--file=/var/log/ost-engine-backup/backup.tgz',
            '--log=/var/log/ost-engine-backup/log.txt',
        ],
    )
    nt.eq_(
        result.code,
        0,
        'Failed to run engine-backup with code {0}. Output: {1}'.format(result.code, result.out)
    )
    result = engine.ssh(
        [
            'engine-backup',
            '--mode=verify',
            '--file=/var/log/ost-engine-backup/backup.tgz',
            '--log=/var/log/ost-engine-backup/verify-log.txt',
        ],
    )
    nt.eq_(
        result.code,
        0,
        'Failed to verify backup with code {0}. Output: {1}'.format(result.code, result.out)
    )


@testlib.with_ovirt_prefix
def download_engine_certs(prefix):
    engine_ip = prefix.virt_env.engine_vm().ip()
    engine_base_url = '/ovirt-engine/services/pki-resource?resource=ca-certificate&format='
    engine_ca_url = engine_base_url + 'X509-PEM-CA'
    engine_ssh_url = engine_base_url + 'OPENSSH-PUBKEY'

    # We use an unverified connection, as L0 host cannot resolve '...engine.lago.local'
    conn = httplib.HTTPSConnection(engine_ip, context=ssl._create_unverified_context())

    def _download_file(url, path):
        conn.request("GET", url)
        resp = conn.getresponse()
        nt.assert_true(
            resp.status == 200
        )
        data = resp.read()
        with open(path, 'wb') as outfile:
            outfile.write(data)

    _download_file(engine_ca_url, 'engine-ca.pem')
    # TODO: verify certificate. Either use it, or run:
    # 'openssl x509 -in engine-ca.pem -text -noout'

    _download_file(engine_ssh_url, 'engine-rsa.pub')
    # TODO: verify public key. Either use it, or run:
    # 'ssh-keygen -l -f engine-rsa.pub'

    conn.close()


@testlib.with_ovirt_api4
def add_vnic_passthrough_profile(api):
    engine = api.system_service()

    vnic_service = test_utils.get_vnic_profiles_service(engine, MANAGEMENT_NETWORK)

    vnic_profile = vnic_service.add(
        profile=sdk4.types.VnicProfile(
            name=PASSTHROUGH_VNIC_PROFILE,
            pass_through=sdk4.types.VnicPassThrough(
                mode=sdk4.types.VnicPassThroughMode.ENABLED
            )
        )
    )
    nt.assert_equals(
        vnic_profile.pass_through.mode, sdk4.types.VnicPassThroughMode.ENABLED
    )


@testlib.with_ovirt_api4
def remove_vnic_passthrough_profile(api):
    engine = api.system_service()

    vnic_service = test_utils.get_vnic_profiles_service(engine, MANAGEMENT_NETWORK)

    vnic_profile = next(vnic_profile for vnic_profile in vnic_service.list()
                        if vnic_profile.name == PASSTHROUGH_VNIC_PROFILE
                        )

    vnic_service.profile_service(vnic_profile.id).remove()
    nt.assert_equals(next((vnic_profile for vnic_profile in vnic_service.list()
                           if vnic_profile.name == PASSTHROUGH_VNIC_PROFILE), None),
                     None)


@testlib.with_ovirt_api
def add_blank_vms(api):
    vm_memory = 256 * MB
    vm_params = params.VM(
        memory=vm_memory,
        os=params.OperatingSystem(
            type_='other_linux',
        ),
        type_='server',
        high_availability=params.HighAvailability(
            enabled=False,
        ),
        cluster=params.Cluster(
            name=CLUSTER_NAME,
        ),
        template=params.Template(
            name=TEMPLATE_BLANK,
        ),
        display=params.Display(
            smartcard_enabled=True,
            keyboard_layout='en-us',
            file_transfer_enabled=True,
            copy_paste_enabled=True,
        ),
        usb=params.Usb(
            enabled=True,
            type_=sdk4.types.UsbType.NATIVE,
        ),
        memory_policy=params.MemoryPolicy(
            guaranteed=vm_memory / 2,
        ),
        name=VM0_NAME
    )
    for vm in [VM0_NAME, VM2_NAME, BACKUP_VM_NAME]:
        vm_params.name = vm
        if vm == VM2_NAME:
            vm_params.high_availability.enabled = True
            vm_params.custom_emulated_machine = 'pc-i440fx-rhel7.4.0'

        api.vms.add(vm_params)
        testlib.assert_true_within_short(
            lambda: api.vms.get(vm).status.state == 'down',
        )


@testlib.with_ovirt_api
def add_nic(api):
    NIC_NAME = 'eth0'
    nic_params = params.NIC(
        name=NIC_NAME,
        interface='virtio',
        network=params.Network(
            name='ovirtmgmt',
        ),
    )
    api.vms.get(VM0_NAME).nics.add(nic_params)

    nic_params.mac = params.MAC(address=UNICAST_MAC_OUTSIDE_POOL)
    nic_params.interface='e1000'
    api.vms.get(VM2_NAME).nics.add(nic_params)


@testlib.with_ovirt_api
def add_graphics_console(api):
    vm = api.vms.get(VM0_NAME)
    vm.graphicsconsoles.add(
        params.GraphicsConsole(
            protocol='vnc',
        )
    )
    testlib.assert_true_within_short(
        lambda:
        len(api.vms.get(VM0_NAME).graphicsconsoles.list()) == 2
    )


@testlib.with_ovirt_api4
def add_filter(ovirt_api4):
    engine = ovirt_api4.system_service()
    nics_service = test_utils.get_nics_service(engine, VM0_NAME)
    nic = nics_service.list()[0]
    network = ovirt_api4.follow_link(nic.vnic_profile).network
    network_filters_service = engine.network_filters_service()
    network_filter = next(
        network_filter for network_filter in network_filters_service.list()
        if network_filter.name == NETWORK_FILTER_NAME
    )
    vnic_profiles_service = engine.vnic_profiles_service()

    vnic_profile = vnic_profiles_service.add(
        sdk4.types.VnicProfile(
            name='{}_profile'.format(network_filter.name),
            network=network,
            network_filter=network_filter
        )
    )
    nic.vnic_profile = vnic_profile
    nt.assert_true(
        nics_service.nic_service(nic.id).update(nic)
    )


@testlib.with_ovirt_prefix
def add_filter_parameter(prefix):
    engine = prefix.virt_env.engine_vm()
    ovirt_api4 = engine.get_api(api_ver=4)
    vm_gw = '.'.join(engine.ip().split('.')[0:3] + ['1'])
    network_filter_parameters_service = test_utils.get_network_fiter_parameters_service(
        ovirt_api4.system_service(), VM0_NAME)

    nt.assert_true(
        network_filter_parameters_service.add(
            sdk4.types.NetworkFilterParameter(
                name=NETWORK_FILTER_PARAMETER0_NAME,
                value=NETWORK_FILTER_PARAMETER0_VALUE
            )
        )
    )

    nt.assert_true(
        network_filter_parameters_service.add(
            sdk4.types.NetworkFilterParameter(
                name=NETWORK_FILTER_PARAMETER1_NAME,
                value=vm_gw
            )
        )
    )


@testlib.with_ovirt_api4
def add_serial_console_vm2(api):
    engine = api.system_service()
    # Find the virtual machine. Note the use of the `all_content` parameter, it is
    # required in order to obtain additional information that isn't retrieved by
    # default, like the configuration of the serial console.
    vm = engine.vms_service().list(search='name={}'.format(VM2_NAME), all_content=True)[0]
    if not vm.console.enabled:
        vm_service = test_utils.get_vm_service(engine, VM2_NAME)
        vm_service.update(
            sdk4.types.Vm(
                console=sdk4.types.Console(
                    enabled=True
                )
            )
        )

@testlib.with_ovirt_api4
def add_instance_type(api):
    instance_types_service = api.system_service().instance_types_service()
    nt.assert_true(
        instance_types_service.add(
            sdk4.types.InstanceType(
                name='myinstancetype',
                description='My instance type',
                memory=1 * GB,
                memory_policy=sdk4.types.MemoryPolicy(
                    max=1 * GB,
                ),
                high_availability=sdk4.types.HighAvailability(
                    enabled=True,
                ),
                cpu=sdk4.types.Cpu(
                    topology=sdk4.types.CpuTopology(
                        cores=2,
                        sockets=2,
                    ),
                ),
            ),
        )
    )


@testlib.with_ovirt_api
def add_event(api):
    event_params = params.Event(
        description='ovirt-system-tests description',
        custom_id=int('01234567890'),
        severity='NORMAL',
        origin='ovirt-system-tests',
        cluster=params.Cluster(
            name=CLUSTER_NAME,
        ),
    )

    nt.assert_true(api.events.add(event_params))


_TEST_LIST = [
    copy_storage_script,
    download_engine_certs,
    add_dc,
    add_cluster,
    add_hosts,
    get_version,
    get_domains,
    get_operating_systems,
    get_system_options,
    get_cluster_levels,
    add_affinity_group,
    add_qos,
    add_bookmark,
    configure_storage,
    list_glance_images,
    add_dc_quota,
    update_default_dc,
    update_default_cluster,
    add_mac_pool,
    remove_default_dc,
    remove_default_cluster,
    add_quota_storage_limits,
    add_quota_cluster_limits,
    set_dc_quota_audit,
    add_role,
    add_scheduling_policy,
    add_affinity_label,
    add_tag,
    add_cpu_profile,
    verify_add_hosts,
    add_master_storage_domain,
    add_disk_profile,
    get_cluster_enabled_features,
    get_host_numa_nodes,
    get_host_devices,
    get_host_hooks,
    get_host_stats,
    add_glance_images,
    add_fence_agent,
    verify_engine_backup,
    verify_notifier,
    check_update_host,
    add_vnic_passthrough_profile,
    remove_vnic_passthrough_profile,
    add_blank_vms,
    add_nic,
    add_graphics_console,
    add_filter,
    add_filter_parameter,
    add_serial_console_vm2,
    add_instance_type,
    add_event,
    verify_add_all_hosts,
    add_secondary_storage_domains,
    import_templates,
    add_non_vm_network,
    add_vm_network,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
