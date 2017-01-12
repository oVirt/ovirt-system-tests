#
# Copyright 2014 Red Hat, Inc.
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
import os
import random

import nose.tools as nt
from nose import SkipTest
from ovirtsdk.infrastructure import errors
from ovirtsdk.xml import params

from lago import utils
from ovirtlago import testlib


# DC/Cluster
DC_NAME = 'test-dc'
DC_VER_MAJ = 4
DC_VER_MIN = 1
SD_FORMAT = 'v4'
CLUSTER_NAME = 'test-cluster'
DC_QUOTA_NAME = 'DC-QUOTA'

# Storage
MASTER_SD_TYPE = 'iscsi'

SD_NFS_NAME = 'nfs'
SD_NFS_HOST_NAME = testlib.get_prefixed_name('engine')
SD_NFS_PATH = '/exports/nfs/share1'

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
CIRROS_IMAGE_NAME = 'CirrOS 0.3.4 for x86_64'

# Network
VLAN200_NET = 'VLAN200_Network'
VLAN100_NET = 'VLAN100_Network'

def _get_host_ip(prefix, host_name):
    return prefix.virt_env.get_vm(host_name).ip()

def _hosts_in_dc(api, dc_name=DC_NAME):
    hosts = api.hosts.list(query='datacenter={}'.format(dc_name))
    return sorted(hosts, key=lambda host: host.name)

def _random_host_from_dc(api, dc_name=DC_NAME):
    return random.choice(_hosts_in_dc(api, dc_name))

@testlib.with_ovirt_api
def add_dc(api):
    p = params.DataCenter(
        name=DC_NAME,
        local=False,
        version=params.Version(
            major=DC_VER_MAJ,
            minor=DC_VER_MIN,
        ),
    )
    nt.assert_true(api.datacenters.add(p))


@testlib.with_ovirt_api
def remove_default_dc(api):
    nt.assert_true(api.datacenters.get(name='Default').delete())


@testlib.with_ovirt_api
def remove_default_cluster(api):
    nt.assert_true(api.clusters.get(name='Default').delete())


@testlib.with_ovirt_api
def add_dc_quota(api):
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
    cpu_family = prefix.virt_env.get_ovirt_cpu_family()
    api = prefix.virt_env.engine_vm().get_api()
    p = params.Cluster(
        name=CLUSTER_NAME,
        cpu=params.CPU(
            id=cpu_family,
        ),
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


@testlib.with_ovirt_prefix
def add_hosts(prefix):
    api = prefix.virt_env.engine_vm().get_api()

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

    def _host_is_up():
        cur_state = api.hosts.get(host.name()).status.state

        if cur_state == 'up':
            return True

        if cur_state == 'install_failed':
            raise RuntimeError('Host %s failed to install' % host.name())
        if cur_state == 'non_operational':
            raise RuntimeError('Host %s is in non operational state' % host.name())

    hosts = prefix.virt_env.host_vms()

    vec = utils.func_vector(_add_host, [(h,) for h in hosts])
    vt = utils.VectorThread(vec)
    vt.start_all()
    nt.assert_true(all(vt.join_all()))

    for host in hosts:
        testlib.assert_true_within(_host_is_up, timeout=15 * 60)

    for host in hosts:
        host.ssh(['rm', '-rf', '/dev/shm/yum', '/dev/shm/*.rpm'])

@testlib.with_ovirt_prefix
def install_cockpit_ovirt(prefix):
    def _install_cockpit_ovirt_on_host(host):
        ret = host.ssh(['yum', '-y', 'install', 'cockpit-ovirt-dashboard'])
        nt.assert_equals(ret.code, 0, '_install_cockpit_ovirt_on_host(): failed to install cockpit-ovirt-dashboard on host %s' % host)
        return True

    hosts = prefix.virt_env.host_vms()
    vec = utils.func_vector(_install_cockpit_ovirt_on_host, [(h,) for h in hosts])
    vt = utils.VectorThread(vec)
    vt.start_all()
    nt.assert_true(all(vt.join_all()), 'not all threads finished: %s' % vt)


def _add_storage_domain(api, p):
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


@testlib.with_ovirt_prefix
def add_master_storage_domain(prefix):
    if MASTER_SD_TYPE == 'iscsi':
        add_iscsi_storage_domain(prefix)
    else:
        add_nfs_storage_domain(prefix)


def add_nfs_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_NFS_NAME, SD_NFS_HOST_NAME, SD_NFS_PATH)


def add_generic_nfs_storage_domain(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format=SD_FORMAT, sd_type='data', nfs_version='v4_1'):
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
    _add_storage_domain(api, p)


@testlib.with_ovirt_prefix
def add_secondary_storage_domains(prefix):
    if MASTER_SD_TYPE == 'iscsi':
        vt = utils.VectorThread(
            [
                functools.partial(import_non_template_from_glance, prefix),
                functools.partial(import_template_from_glance, prefix),
                functools.partial(add_nfs_storage_domain, prefix),
                functools.partial(add_iso_storage_domain, prefix),
                functools.partial(add_templates_storage_domain, prefix),
            ],
        )
    else:
        vt = utils.VectorThread(
            [
                functools.partial(import_non_template_from_glance, prefix),
                functools.partial(import_template_from_glance, prefix),
                functools.partial(add_iscsi_storage_domain, prefix),
                functools.partial(add_iso_storage_domain, prefix),
                functools.partial(add_templates_storage_domain, prefix),
            ],
        )
    vt.start_all()
    vt.join_all()


def add_iscsi_storage_domain(prefix):
    api = prefix.virt_env.engine_vm().get_api()

    # Find LUN GUIDs
    ret = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)

    lun_guids = ret.out.splitlines()[:SD_ISCSI_NR_LUNS]

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
    _add_storage_domain(api, p)


def add_iso_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_ISO_NAME, SD_ISO_HOST_NAME, SD_ISO_PATH, sd_format='v1', sd_type='iso', nfs_version='v3')


def add_templates_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_TEMPLATES_NAME, SD_TEMPLATES_HOST_NAME, SD_TEMPLATES_PATH, sd_format='v1', sd_type='export')


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


def generic_import_from_glance(api, image_name=CIRROS_IMAGE_NAME, as_template=False, image_ext='_glance_disk', template_ext='_glance_template', dest_storage_domain=MASTER_SD_TYPE, dest_cluster=CLUSTER_NAME):
    glance_provider = api.storagedomains.get(SD_GLANCE_NAME)
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

    testlib.assert_true_within_long(
        lambda: api.disks.get(disk_name).status.state == 'ok',
    )


@testlib.with_ovirt_api
def list_glance_images(api):
    global GLANCE_AVAIL
    glance_provider = api.storagedomains.get(SD_GLANCE_NAME)
    if glance_provider is None:
        raise SkipTest('%s: GLANCE is not available.' % list_glance_images.__name__ )

    try:
        all_images = glance_provider.images.list()
        if len(all_images):
            GLANCE_AVAIL = True
    except errors.RequestError:
        raise SkipTest('%s: GLANCE is not available: client request error' % list_glance_images.__name__ )


def import_non_template_from_glance(prefix):
    api = prefix.virt_env.engine_vm().get_api()
    if not GLANCE_AVAIL:
        raise SkipTest('%s: GLANCE is not available.' % import_non_template_from_glance.__name__ )
    generic_import_from_glance(api)


def import_template_from_glance(prefix):
    api = prefix.virt_env.engine_vm().get_api()
    if not GLANCE_AVAIL:
        raise SkipTest('%s: GLANCE is not available.' % import_template_from_glance.__name__ )
    generic_import_from_glance(api, image_name=CIRROS_IMAGE_NAME, image_ext='_glance_template', as_template=True)


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


@testlib.with_ovirt_api
def add_vm_network(api):
    dc = api.datacenters.get(DC_NAME)
    VLAN100 = params.Network(
        name=VLAN100_NET,
        data_center=params.DataCenter(
            name=DC_NAME,
        ),
        description='VM Network on VLAN 100',
        vlan=params.VLAN(
            id='100',
        ),
    )

    nt.assert_true(
        api.networks.add(VLAN100)
    )
    nt.assert_true(
        api.clusters.get(CLUSTER_NAME).networks.add(VLAN100)
    )


@testlib.with_ovirt_api
def add_non_vm_network(api):
    dc = api.datacenters.get(DC_NAME)
    VLAN200 = params.Network(
        name=VLAN200_NET,
        data_center=params.DataCenter(
            name=DC_NAME,
        ),
        description='Non VM Network on VLAN 200, MTU 9000',
        vlan=params.VLAN(
            id='200',
        ),
        usages=params.Usages(),
        mtu=9000,
    )

    nt.assert_true(
        api.networks.add(VLAN200)
    )
    nt.assert_true(
        api.clusters.get(CLUSTER_NAME).networks.add(VLAN200)
    )


@testlib.with_ovirt_prefix
def run_log_collector(prefix):
    engine = prefix.virt_env.engine_vm()
    result = engine.ssh(
        [
            'ovirt-log-collector',
            '--conf-file=/root/ovirt-log-collector.conf',
        ],
    )
    nt.eq_(
        result.code, 0, 'log collector failed. Exit code is %s' % result.code
    )

    engine.ssh(
        [
            'rm',
            '-rf',
            '/dev/shm/sosreport-LogCollector-*',
        ],
    )


_TEST_LIST = [
    add_dc,
    add_cluster,
    add_hosts,
    add_master_storage_domain,
    list_glance_images,
    add_secondary_storage_domains,
    import_templates,
    run_log_collector,
    add_non_vm_network,
    add_vm_network,
    remove_default_dc,
    remove_default_cluster,
    add_dc_quota,
    add_quota_storage_limits,
    add_quota_cluster_limits,
    set_dc_quota_audit,
    install_cockpit_ovirt,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
