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
import json
import os
import random
import time

import nose.tools as nt
from nose import SkipTest
from ovirtsdk.infrastructure import errors
from ovirtsdk.xml import params
try:
    import ovirtsdk4 as sdk4
    API_V3_ONLY = os.getenv('API_V3_ONLY', False)
    if API_V3_ONLY:
        API_V4 = False
    else:
        API_V4 = True
except ImportError:
    API_V4 = False

from lago import utils
from ovirtlago import testlib


# DC/Cluster
DC_NAME = 'Default'
DC_VER_MAJ = 4
DC_VER_MIN = 1
SD_FORMAT = 'v4'
CLUSTER_NAME = 'Default'
DC_QUOTA_NAME = 'DC-QUOTA'
HE_DC_NAME = 'Default'
HE_CLUSTER_NAME = 'Default'

# Storage
MASTER_SD_TYPE = 'iscsi'

SD_NFS_NAME = 'nfs'
SD_NFS_HOST_NAME = testlib.get_prefixed_name('storage')
SD_NFS_PATH = '/exports/nfs/share1'

SD_ISCSI_NAME = 'iscsi'
SD_ISCSI_HOST_NAME = testlib.get_prefixed_name('storage')
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
GLANCE_SERVER_URL = 'http://glance.ovirt.org:9292/'

# Network
VLAN200_NET = 'VLAN200_Network'
VLAN100_NET = 'VLAN100_Network'


def _get_host_ip(prefix, host_name):
    return prefix.virt_env.get_vm(host_name).ip()

def _hosts_in_dc(api, dc_name=DC_NAME):
    hosts = api.hosts.list(query='datacenter={} AND status=up'.format(dc_name))
    if hosts:
        return sorted(hosts, key=lambda host: host.name)
    raise RuntimeError('Could not find hosts that are up in DC %s' % dc_name)

def _hosts_in_dc_4(api, dc_name=DC_NAME):
    hosts_service = api.system_service().hosts_service()
    hosts = hosts_service.list(search='datacenter={} AND status=up'.format(dc_name))
    if hosts:
        return sorted(hosts, key=lambda host: host.name)
    raise RuntimeError('Could not find hosts that are up in DC %s' % dc_name)

def _random_host_from_dc(api, dc_name=DC_NAME):
    return random.choice(_hosts_in_dc(api, dc_name))

def _random_host_from_dc_4(api, dc_name=DC_NAME):
    return random.choice(_hosts_in_dc_4(api, dc_name))


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
    dcs_service = api.system_service().data_centers_service()
    search_query='name=Default'
    dc = dcs_service.list(search=search_query)[0]
    dc_service = dcs_service.data_center_service(dc.id)
    dc_service.remove()


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
    clusters_services = api.system_service().clusters_service()
    search_query='name=Default'
    cluster=clusters_services.list(search=search_query)[0]
    cl_service = clusters_services.cluster_service(cluster.id)
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


def add_cluster_4(prefix):
    cpu_family = prefix.virt_env.get_ovirt_cpu_family()
    api = prefix.virt_env.engine_vm().get_api(api_ver=4)
    clusters_service = api.system_service().clusters_service()
    nt.assert_true(
        clusters_service.add(
            sdk4.types.Cluster(
                name=CLUSTER_NAME,
                description='APIv4 Cluster',
                cpu=sdk4.types.Cpu(
                    architecture=sdk4.types.Architecture.X86_64,
                    type=cpu_family,
                ),
                data_center=sdk4.types.DataCenter(
                    name=DC_NAME,
                ),
                ballooning_enabled=True,
            ),
        )
    )


@testlib.with_ovirt_prefix
def add_hosts(prefix):
    if API_V4:
        add_hosts_4(prefix)
    else:
        add_hosts_3(prefix)


def add_hosts_3(prefix):
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


def add_hosts_4(prefix):
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
        if host_obj.status == sdk4.types.HostStatus.UP:
            return True

        if host_obj.status == sdk4.types.HostStatus.NON_OPERATIONAL:
            raise RuntimeError('Host %s is in non operational state' % api_host.name)
        if host_obj.status == sdk4.types.HostStatus.INSTALL_FAILED:
            raise RuntimeError('Host %s installation failed' % api_host.name)
        if host_obj.status == sdk4.types.HostStatus.NON_RESPONSIVE:
            raise RuntimeError('Host %s is in non responsive state' % api_host.name)


    hosts = prefix.virt_env.host_vms()
    vec = utils.func_vector(_add_host_4, [(h,) for h in hosts])
    vt = utils.VectorThread(vec)
    vt.start_all()
    nt.assert_true(all(vt.join_all()))

    api_hosts = hosts_service.list()
    for api_host in api_hosts:
        testlib.assert_true_within(_host_is_up_4, timeout=15*60)

    for host in hosts:
        host.ssh(['rm', '-rf', '/dev/shm/yum', '/dev/shm/*.rpm'])


@testlib.with_ovirt_prefix
def add_he_hosts(prefix):
    if API_V4:
        add_he_hosts_4(prefix)
    else:
        raise RuntimeError('Adding HE hosts requires API v4.')


def add_he_hosts_4(prefix):
    api = prefix.virt_env.engine_vm().get_api_v4()
    hosts_service = api.system_service().hosts_service()

    def _add_he_host_4(vm):
        return hosts_service.add(
            sdk4.types.Host(
                name=vm.name(),
                description='host %s' % vm.name(),
                address=vm.name(),
                root_password=str(vm.root_password()),
                override_iptables=True,
                cluster=sdk4.types.Cluster(
                    name=HE_CLUSTER_NAME,
                ),
            ),
            deploy_hosted_engine=True,
        )

    def _he_host_is_up_4():
        host_service = hosts_service.host_service(api_host.id)
        host_obj = host_service.get()
        if host_obj.status == sdk4.types.HostStatus.UP:
            return True

        if host_obj.status == sdk4.types.HostStatus.NON_OPERATIONAL:
            raise RuntimeError('Host %s is in non operational state' % api_host.name)
        if host_obj.status == sdk4.types.HostStatus.INSTALL_FAILED:
            raise RuntimeError('Host %s installation failed' % api_host.name)
        if host_obj.status == sdk4.types.HostStatus.NON_RESPONSIVE:
            raise RuntimeError('Host %s is in non responsive state' % api_host.name)


    hosts = prefix.virt_env.host_vms()
    vec = utils.func_vector(_add_he_host_4, [(h,) for h in hosts if not h.name().endswith('t0')])
    vt = utils.VectorThread(vec)
    vt.start_all()
    nt.assert_true(all(vt.join_all()))

    api_hosts = hosts_service.list()
    for api_host in api_hosts:
        testlib.assert_true_within(_he_host_is_up_4, timeout=15*60)

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

    def _is_sd_unattached():
        usd = sd_service.get()
        if usd.status == sdk4.types.StorageDomainStatus.UNATTACHED:
            return True

    testlib.assert_true_within_long(
        _is_sd_unattached
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

    def _is_sd_active():
        asd = attached_sd_service.get()
        if asd.status == sdk4.types.StorageDomainStatus.ACTIVE:
            return True

    testlib.assert_true_within_long(
        _is_sd_active
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


def add_generic_nfs_storage_domain_4(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format='v4', sd_type='data', nfs_version='v4_1'):
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
    # FIXME
    # if API_V4:
    #    return add_iscsi_storage_domain_4(prefix)

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
    _add_storage_domain_3(api, p)


def add_iscsi_storage_domain_4(prefix):
    api = prefix.virt_env.engine_vm().get_api_v4()
    ret = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)

    lun_guids = ret.out.splitlines()[:SD_ISCSI_NR_LUNS]
    #FIXME

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

@testlib.with_ovirt_prefix
def list_glance_images(prefix):
    if API_V4:
        api = prefix.virt_env.engine_vm().get_api(api_ver=4)
        list_glance_images_4(api)
    else:
        api = prefix.virt_env.engine_vm().get_api()
        list_glance_images_3(api)


@testlib.with_ovirt_prefix
def wait_engine(prefix):

    def _engine_is_up():
        engine = prefix.virt_env.engine_vm()
        try:
            if engine and engine.get_api():
                return True
        except:
            return

    testlib.assert_true_within(_engine_is_up, timeout=20 * 60)


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
    glance_domain_list = api.system_service().storage_domains_service().list(search=search_query)

    if not glance_domain_list:
        openstack_glance = add_glance_4(api)
        if not openstack_glance:
            raise SkipTest('%s GLANCE storage domain is not available.' % list_glance_images_4.__name__ )
        glance_domain_list = api.system_service().storage_domains_service().list(search=search_query)

    if not check_glance_connectivity_4(api):
        raise SkipTest('%s: GLANCE connectivity test failed' % list_glance_images_4.__name__ )

    glance_domain = glance_domain_list.pop()
    glance_domain_service = api.system_service().storage_domains_service().storage_domain_service(glance_domain.id)

    try:
        all_images = glance_domain_service.images_service().list()
        if len(all_images):
            GLANCE_AVAIL = True
    except errors.RequestError:
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
        except errors.RequestError:
            pass

    return avail


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

@testlib.with_ovirt_prefix
def sleep(prefix):
    time.sleep(120)


@testlib.with_ovirt_prefix
def he_vm_status(prefix):
    host0 = sorted(prefix.virt_env.host_vms(), key=lambda h: h.name())[0]
    result = host0.ssh(
        [
            'hosted-engine',
            '--vm-status',
            '--json',
        ],
    )
    nt.eq_(
        result.code, 0, 'hosted-engine --vm-status exit code: %s' % result.code
    )

    try:
        vm_status = json.loads(result.out)
        if vm_status['1']['engine-status']['health'] != 'good':
            raise RuntimeError('engine-status is not good: %s' % vm_status)
    except ValueError:
        raise RuntimeError('could not parse JSON: %s' % result.out)


_TEST_LIST = [
    wait_engine,
#    add_dc,
#    add_cluster,
    add_master_storage_domain,
    he_vm_status,
    sleep,
    add_he_hosts,
    list_glance_images,
    add_secondary_storage_domains,
#    import_templates,
#    run_log_collector,
    add_non_vm_network,
    add_vm_network,
    add_dc_quota,
#    remove_default_dc,
#    remove_default_cluster,
    add_quota_storage_limits,
    add_quota_cluster_limits,
    set_dc_quota_audit,
    install_cockpit_ovirt,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
