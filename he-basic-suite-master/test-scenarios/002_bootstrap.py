# -*- coding: utf-8 -*-
#
# Copyright 2014-2019 Red Hat, Inc.
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

from six.moves import http_client

import nose.tools as nt
from nose import SkipTest
from ovirtsdk4 import Error as sdkError
import ovirtsdk4.types as types

import test_utils
from test_utils import versioning
from test_utils import ipv6_utils
from test_utils import network_utils_v4

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

import logging
LOGGER = logging.getLogger(__name__)

# DC/Cluster
DC_NAME = 'Default'
DC_VER_MAJ = 4
DC_VER_MIN = 2
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
GUEST_IMAGE_NAME = versioning.guest_os_image_name()
GLANCE_DISK_NAME = versioning.guest_os_glance_disk_name()
TEMPLATE_GUEST = versioning.guest_os_template_name()
GLANCE_SERVER_URL = 'http://glance.ovirt.org:9292/'

# Network
VLAN200_NET = 'VLAN200_Network'
VLAN100_NET = 'VLAN100_Network'

IPV6_ONLY = os.getenv('IPV6_ONLY', False)
# Network
VM_NETWORK = u'VM Network with a very long name and עברית'
VM_NETWORK_VLAN_ID = 100
MIGRATION_NETWORK = 'Migration_Net'


def setup_module():
    ipv6_utils.open_connection_to_api_with_ipv6_on_relevant_suite()


def _get_host_ip(prefix, host_name):
    return prefix.virt_env.get_vm(host_name).ip()


def _get_host_ips_in_net(prefix, host_name, net_name):
    return prefix.virt_env.get_vm(host_name).ips_in_net(net_name)


def _create_url_for_host(prefix, host_name):
    ip = prefix.virt_env.get_vm(host_name).ip()
    if IPV6_ONLY:
        return '[%s]' % ip
    return ip

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


@testlib.with_ovirt_api4
def add_dc(api):
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


@testlib.with_ovirt_api4
def add_dc_quota(api):
    datacenters_service = api.system_service().data_centers_service()
    datacenter = datacenters_service.list(search='name=%s' % DC_NAME)[0]
    datacenter_service = datacenters_service.data_center_service(datacenter.id)
    quotas_service = datacenter_service.quotas_service()
    nt.assert_true(
        quotas_service.add(
            types.Quota (
                name=DC_QUOTA_NAME,
                description='DC-QUOTA-DESCRIPTION',
                data_center=datacenter,
                cluster_soft_limit_pct=99
            )
        )
    )


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


    hosts = sorted(prefix.virt_env.host_vms(), key=lambda host: host.name())[1:]
    vec = utils.func_vector(_add_he_host_4, [(h,) for h in hosts])
    vt = utils.VectorThread(vec)
    vt.start_all()
    nt.assert_true(all(vt.join_all()))

    api_hosts = hosts_service.list()
    for api_host in api_hosts:
        testlib.assert_true_within(_he_host_is_up_4, timeout=15*60)

    for host in hosts:
        host.ssh(['rm', '-rf', '/var/cache/yum/*', '/var/cache/dnf/*'])


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


def add_iscsi_storage_domain_4(prefix):
    api = prefix.virt_env.engine_vm().get_api_v4()

    # Find LUN GUIDs
    ret = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)

    lun_guids = ret.out.splitlines()[:SD_ISCSI_NR_LUNS]
    ips = []
    ips.append(_get_host_ip(prefix, SD_ISCSI_HOST_NAME))

    luns = []
    for lun_id in lun_guids:
        for ip in ips:
            lun=sdk4.types.LogicalUnit(
                id=lun_id.decode('utf-8'),
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
        add_iscsi_storage_domain_4(prefix)
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

    api = prefix.virt_env.engine_vm().get_api_v4()
    ips = _get_host_ips_in_net(prefix, nfs_host_name, testlib.get_prefixed_name('net-management'))
    kwargs = {}
    if sd_format >= 'v4':
        if not versioning.cluster_version_ok(4, 1):
            kwargs['storage_format'] = sdk4.types.StorageFormat.V3
        elif not versioning.cluster_version_ok(4, 3):
            kwargs['storage_format'] = sdk4.types.StorageFormat.V4
    random_host = _random_host_from_dc_4(api, DC_NAME)
    LOGGER.debug('random host: {}'.format(random_host.name))
    p = sdk4.types.StorageDomain(
        name=sd_nfs_name,
        description='APIv4 NFS storage domain',
        type=dom_type,
        host=random_host,
        storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.NFS,
            address=ips[0],
            path=mount_path,
            nfs_version=nfs_vers,
        ),
        **kwargs
    )

    _add_storage_domain(api, p)

@testlib.with_ovirt_prefix
def add_secondary_storage_domains(prefix):
    if MASTER_SD_TYPE == 'iscsi':
        vt = utils.VectorThread(
            [
                functools.partial(add_nfs_storage_domain, prefix),
                functools.partial(add_iso_storage_domain, prefix),
                functools.partial(add_templates_storage_domain, prefix),
            ],
        )
    else:
        vt = utils.VectorThread(
            [
                functools.partial(add_iscsi_storage_domain, prefix),
                functools.partial(add_iso_storage_domain, prefix),
                functools.partial(add_templates_storage_domain, prefix),
            ],
        )
    vt.start_all()
    vt.join_all()

@testlib.with_ovirt_api4
@testlib.with_ovirt_prefix
def add_glance_storage(prefix,api):
    engine = api.system_service()
    vt = utils.VectorThread(
        [
            functools.partial(import_non_template_from_glance, prefix),
            functools.partial(import_template_from_glance, prefix),
        ],
    )
    vt.start_all()
    vt.join_all()

    with test_utils.TestEvent(engine, 3018):
        print('done adding disk')

def add_iscsi_storage_domain(prefix):
    # FIXME
    # if API_V4:
    #    return add_iscsi_storage_domain_4(prefix)

    api = prefix.virt_env.engine_vm().get_api_v4()

    # Find LUN GUIDs
    ret = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)

    lun_guids = ret.out.splitlines()[:SD_ISCSI_NR_LUNS]

    p = types.StorageDomain(
        name=SD_ISCSI_NAME,
        data_center=types.DataCenter(
            name=DC_NAME,
        ),
        type_='data',
        storage_format=SD_FORMAT,
        host=_random_host_from_dc_4(api, DC_NAME),
        storage=types.Storage(
            type_='iscsi',
            volume_group=types.VolumeGroup(
                logical_unit=[
                    types.LogicalUnit(
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


def add_iscsi_storage_domain_bad(prefix):
    luns = test_utils.get_luns(
        prefix, SD_ISCSI_HOST_NAME, SD_ISCSI_PORT, SD_ISCSI_TARGET, from_lun=0, to_lun=SD_ISCSI_NR_LUNS)

    v4_domain = versioning.cluster_version_ok(4, 1)
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


def add_iso_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_ISO_NAME, SD_ISO_HOST_NAME, SD_ISO_PATH, sd_format='v1', sd_type='iso', nfs_version='v3')


def add_templates_storage_domain(prefix):
    add_generic_nfs_storage_domain(prefix, SD_TEMPLATES_NAME, SD_TEMPLATES_HOST_NAME, SD_TEMPLATES_PATH, sd_format='v1', sd_type='export')


def generic_import_from_glance(prefix=None, as_template=False,
                               dest_storage_domain=MASTER_SD_TYPE,
                               dest_cluster=CLUSTER_NAME):
    api = prefix.virt_env.engine_vm().get_api_v4()
    storage_domains_service = api.system_service().storage_domains_service()
    glance_storage_domain = storage_domains_service.list(search='name={}'.format(SD_GLANCE_NAME))[0]
    images = storage_domains_service.storage_domain_service(glance_storage_domain.id).images_service().list()
    image = [x for x in images if x.name == GUEST_IMAGE_NAME][0]
    image_service = storage_domains_service.storage_domain_service(glance_storage_domain.id).images_service().image_service(image.id)
    result = image_service.import_(
        storage_domain=types.StorageDomain(
           name=dest_storage_domain,
        ),
        template=types.Template(
            name=TEMPLATE_GUEST,
        ),
        cluster=types.Cluster(
           name=dest_cluster,
        ),
        import_as_template=as_template,
        disk=types.Disk(
            name=(TEMPLATE_GUEST if as_template else GLANCE_DISK_NAME)
        ),
    )
    disk = api.system_service().disks_service().list(search='name={}'.format(TEMPLATE_GUEST if as_template else GLANCE_DISK_NAME))[0]
    nt.assert_true(disk)


@testlib.with_ovirt_prefix
def wait_engine(prefix):

    def _engine_is_up():
        print('API_V4: %s' % API_V4)
        engine = prefix.virt_env.engine_vm()
        try:
            if engine and engine.get_api_v4():
                return True
        except:
            return

    testlib.assert_true_within(_engine_is_up, timeout=20 * 60)


@testlib.with_ovirt_api4
def list_glance_images(api):
    global GLANCE_AVAIL
    search_query = 'name={}'.format(SD_GLANCE_NAME)
    glance_domain_list = api.system_service().storage_domains_service().list(search=search_query)

    if not glance_domain_list:
        openstack_glance = add_glance(api)
        if not openstack_glance:
            raise SkipTest('%s GLANCE storage domain is not available.' % list_glance_images.__name__ )
        glance_domain_list = api.system_service().storage_domains_service().list(search=search_query)

    if not check_glance_connectivity(api):
        raise SkipTest('%s: GLANCE connectivity test failed' % list_glance_images.__name__ )

    glance_domain = glance_domain_list.pop()
    glance_domain_service = api.system_service().storage_domains_service().storage_domain_service(glance_domain.id)

    try:
        all_images = glance_domain_service.images_service().list()
        if len(all_images):
            GLANCE_AVAIL = True
    except sdkError as e:
        if e.code == http_client.BAD_REQUEST:
            raise SkipTest('%s: GLANCE is not available: client request error'
                           % list_glance_images.__name__)
        else:
            raise



def add_glance(api):
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

        testlib.assert_true_within_short(func=get,
                                         allowed_exceptions=[sdkError])
    except (AssertionError, sdkError):
        # RequestError if add method was failed.
        # AssertionError if add method succeed but we couldn't verify that glance was actually added
        return None

    return glance.pop()


def check_glance_connectivity(api):
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
        except sdkError as e:
            if e.code == http_client.BAD_REQUEST:
                pass
            else:
                raise

    return avail


def import_non_template_from_glance(prefix_param):
    if not GLANCE_AVAIL:
        raise SkipTest('%s: GLANCE is not available.' % import_non_template_from_glance.__name__ )
    generic_import_from_glance(prefix=prefix_param)


def import_template_from_glance(prefix_param):
    if not GLANCE_AVAIL:
        raise SkipTest('%s: GLANCE is not available.' % import_template_from_glance.__name__ )
    generic_import_from_glance(prefix=prefix_param, as_template=True)


@testlib.with_ovirt_api4
def set_dc_quota_audit(api):
    dcs_service = api.system_service().data_centers_service()
    dc = dcs_service.list(search='name=%s' % DC_NAME)[0]
    dc_service = dcs_service.data_center_service(dc.id)
    nt.assert_true(
        dc_service.update(
            types.DataCenter(
                quota_mode=types.QuotaModeType.AUDIT,
            ),
        )
   )


@testlib.with_ovirt_api4
def add_quota_storage_limits(api):

    # Find the data center and the service that manages it:
    dcs_service = api.system_service().data_centers_service()
    dc = dcs_service.list(search='name=%s' % DC_NAME)[0]
    dc_service = dcs_service.data_center_service(dc.id)

    # Find the storage domain and the service that manages it:
    sds_service = api.system_service().storage_domains_service()
    sd = sds_service.list()[0]

    # Find the quota and the service that manages it.
    # If the quota doesn't exist,create it.
    quotas_service = dc_service.quotas_service()
    quotas = quotas_service.list()

    quota = next(
        (q for q in quotas if q.name == DC_QUOTA_NAME ),
        None
    )
    if quota is None:
        quota = quotas_service.add(
            quota=types.Quota(
                name=DC_QUOTA_NAME,
                description='DC-QUOTA-DESCRIPTION',
                cluster_hard_limit_pct=20,
                cluster_soft_limit_pct=80,
                storage_hard_limit_pct=20,
                storage_soft_limit_pct=80
            )
        )
    quota_service = quotas_service.quota_service(quota.id)

    # Find the quota limit for the storage domain that we are interested on:
    limits_service = quota_service.quota_storage_limits_service()
    limits = limits_service.list()
    limit = next(
        (l for l in limits if l.id == sd.id),
        None
    )

    # If that limit exists we will delete it:
    if limit is not None:
        limit_service = limits_service.limit_service(limit.id)
        limit_service.remove()

    # Create the limit again, with the desired value
    nt.assert_true(
        limits_service.add(
            limit=types.QuotaStorageLimit(
                limit=500,
            )
        )
    )


@testlib.with_ovirt_api4
def add_quota_cluster_limits(api):
    datacenters_service = api.system_service().data_centers_service()
    datacenter = datacenters_service.list(search='name=%s' % DC_NAME)[0]
    datacenter_service = datacenters_service.data_center_service(datacenter.id)
    quotas_service = datacenter_service.quotas_service()
    quotas = quotas_service.list()
    quota = next(
        (q for q in quotas if q.name == DC_QUOTA_NAME),
        None
    )
    quota_service = quotas_service.quota_service(quota.id)
    quota_cluster_limits_service = quota_service.quota_cluster_limits_service()
    nt.assert_true(
        quota_cluster_limits_service.add(
            types.QuotaClusterLimit(
                vcpu_limit=20,
                memory_limit=10000.0
            )
        )
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

    with test_utils.TestEvent(engine, 942): # NETWORK_ADD_NETWORK event
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

    with test_utils.TestEvent(engine, 942): # NETWORK_ADD_NETWORK event
        nt.assert_true(
            engine.networks_service().add(network)
        )

    cluster_service = test_utils.get_cluster_service(engine, CLUSTER_NAME)
    nt.assert_true(
        cluster_service.networks_service().add(network)
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


@testlib.with_ovirt_prefix
def he_get_shared_config(prefix):
    host0 = sorted(prefix.virt_env.host_vms(), key=lambda h: h.name())[0]
    # There was a bug, that 'hosted-engine --get-shared-config' wrote local vm.conf
    # with bad permissions, if it was missing. So remove it, run this, then test sanity.
    host0.ssh(
        [
            'rm',
            '-fv',
            '/var/run/ovirt-hosted-engine-ha/vm.conf',
        ],
    )
    # In 4.2 we have 'he_shared', in 4.1 currently 'he_conf'
    result = host0.ssh(
        [
            'hosted-engine',
            '--get-shared-config',
            'gateway',
	    '--type=he_shared',
	    '||',
            'hosted-engine',
            '--get-shared-config',
            'gateway',
	    '--type=he_conf',
        ],
    )
    nt.eq_(
        result.code, 0, 'hosted-engine --get-shared-config code: %s' % result.code
    )
    nt.assert_true(
	b'gateway' in result.out
    )


@testlib.with_ovirt_prefix
def he_check_ha_agent(prefix):
    host0 = sorted(prefix.virt_env.host_vms(), key=lambda h: h.name())[0]
    # Test that ha agent does not emit errors after he_get_shared_config
    result = host0.ssh(
        [
            'grep',
	    'Permission denied',
            '/var/log/ovirt-hosted-engine-ha/agent.log'
        ],
    )
    nt.assert_true(
	b'Permission denied' not in result.out
    )


_TEST_LIST = [
    wait_engine,
#    add_dc,
    add_master_storage_domain,
    he_vm_status,
    he_get_shared_config,
    sleep,
    add_he_hosts,
    he_check_ha_agent,
    list_glance_images,
    add_glance_storage,
    add_secondary_storage_domains,
#    run_log_collector,
    add_non_vm_network,
    add_vm_network,
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
