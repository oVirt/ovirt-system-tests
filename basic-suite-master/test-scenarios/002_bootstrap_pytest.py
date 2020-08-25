# -*- coding: utf-8 -*-
#
# Copyright 2014, 2017, 2019 Red Hat, Inc.
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
from __future__ import absolute_import

import functools
import os
import random
import ssl
import tempfile
import time

from six.moves import http_client

# TODO: import individual SDKv4 types directly (but don't forget sdk4.Error)
import ovirtsdk4 as sdk4
import ovirtsdk4.types as types
import pytest

from lago import utils
from ovirtlago import testlib

import test_utils
from test_utils import network_utils_v4
from test_utils import constants
from test_utils import versioning

from ost_utils import assertions
from ost_utils import engine_utils
from ost_utils import general_utils
from ost_utils.pytest import order_by
from ost_utils.pytest.fixtures import api_v4
from ost_utils.pytest.fixtures import prefix
from ost_utils.pytest.fixtures import root_password
from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.network import storage_network_name
from ost_utils.selenium.common import http_proxy_disabled
from ost_utils.storage_utils import domain
from ost_utils.storage_utils import glance
from ost_utils.storage_utils import lun
from ost_utils.storage_utils import nfs
from ost_utils import shell

import logging
LOGGER = logging.getLogger(__name__)

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
# TODO temporarily use nfs instead of iscsi. Revert back once iscsi works in vdsm 4.4!
MASTER_SD_TYPE = 'nfs'

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
DLUN_DISK_NAME = 'DirectLunDisk'

SD_ISO_NAME = 'iso'
SD_ISO_HOST_NAME = SD_NFS_HOST_NAME
SD_ISO_PATH = '/exports/nfs/iso'

SD_TEMPLATES_NAME = 'templates'
SD_TEMPLATES_HOST_NAME = SD_NFS_HOST_NAME
SD_TEMPLATES_PATH = '/exports/nfs/exported'

SD_GLANCE_NAME = 'ovirt-image-repository'
GUEST_IMAGE_NAME = versioning.guest_os_image_name()
GLANCE_DISK_NAME = versioning.guest_os_glance_disk_name()
TEMPLATE_GUEST = versioning.guest_os_template_name()
# intentionaly use URL ending with / to test backward compatibility of <4.4 glance implementation and ability to handle // in final URL
GLANCE_SERVER_URL = 'http://glance.ovirt.org:9292/'

# Network
VM_NETWORK = u'VM Network with a very long name and עברית'
VM_NETWORK_VLAN_ID = 100
MIGRATION_NETWORK = 'Migration_Net'
MANAGEMENT_NETWORK = 'ovirtmgmt'
PASSTHROUGH_VNIC_PROFILE = 'passthrough_vnic_profile'
NETWORK_FILTER_NAME = 'clean-traffic'

VM0_NAME = 'vm0'
VM1_NAME = 'vm1'
VM2_NAME = 'vm2'
BACKUP_VM_NAME = 'backup_vm'

# the default MAC pool has addresses like 00:1a:4a:16:01:51
UNICAST_MAC_OUTSIDE_POOL = '0a:1a:4a:16:01:51'


_TEST_LIST = [
    "test_verify_engine_certs",
    "test_engine_health_status",
    "test_add_dc",
    "test_add_cluster",
    "test_add_hosts",
    "test_sync_time",
    "test_get_version",
    "test_get_domains",
    "test_get_operating_systems",
    "test_get_system_options",
    "test_get_cluster_levels",
    "test_add_affinity_group",
    "test_add_qos",
    "test_add_bookmark",
    "test_list_glance_images",
    "test_add_dc_quota",
    "test_update_default_dc",
    "test_update_default_cluster",
    "test_add_mac_pool",
    "test_remove_default_dc",
    "test_remove_default_cluster",
    "test_add_quota_storage_limits",
    "test_add_quota_cluster_limits",
    "test_set_dc_quota_audit",
    "test_add_role",
    "test_add_scheduling_policy",
    "test_add_affinity_label",
    "test_add_tag",
    "test_add_cpu_profile",
    "test_verify_add_hosts",
    "test_add_nfs_master_storage_domain",
    "test_add_iscsi_master_storage_domain",
    "test_add_blank_vms",
    "test_add_direct_lun_vm0",
    "test_add_blank_high_perf_vm2",
    "test_configure_high_perf_vm2",
    "test_add_disk_profile",
    "test_get_cluster_enabled_features",
    "test_get_host_numa_nodes",
    "test_add_glance_images",
    "test_add_fence_agent",
    "test_verify_notifier",
    "test_check_update_host",
    "test_add_vnic_passthrough_profile",
    "test_remove_vnic_passthrough_profile",
    "test_add_nic",
    "test_add_graphics_console",
    "test_add_filter",
    "test_add_filter_parameter",
    "test_add_serial_console_vm2",
    "test_add_instance_type",
    "test_add_event",
    "test_verify_add_all_hosts",
    "test_complete_hosts_setup",
    "test_get_host_devices",
    "test_get_host_hooks",
    "test_get_host_stats",
    "test_add_secondary_storage_domains",
    "test_resize_and_refresh_storage_domain",
    "test_add_vm2_lease",
    "test_add_non_vm_network",
    "test_add_vm_network",
    "test_verify_glance_import",
    "test_verify_engine_backup",
]


def _hosts_in_dc(api, dc_name=DC_NAME, random_host=False):
    hosts_service = api.system_service().hosts_service()
    all_hosts = _wait_for_status(hosts_service, dc_name, types.HostStatus.UP)
    up_hosts = [host for host in all_hosts if host.status == types.HostStatus.UP]
    if up_hosts:
        if random_host:
            return random.choice(up_hosts)
        else:
            return sorted(up_hosts, key=lambda host: host.name)
    hosts_status = [host for host in all_hosts if host.status != types.HostStatus.UP]
    dump_hosts = _host_status_to_print(hosts_service, hosts_status)
    raise RuntimeError('Could not find hosts that are up in DC {} \nHost status: {}'.format(dc_name, dump_hosts) )

def _random_host_from_dc(api, dc_name=DC_NAME):
    return _hosts_in_dc(api, dc_name, True)

def _random_host_service_from_dc(api, dc_name=DC_NAME):
    host = _hosts_in_dc(api, dc_name, True)
    return api.system_service().hosts_service().host_service(id=host.id)

def _all_hosts_up(hosts_service, total_num_hosts):
    installing_hosts = hosts_service.list(search='datacenter={} AND status=installing or status=initializing or status=connecting'.format(DC_NAME))
    if len(installing_hosts) == total_num_hosts: # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(DC_NAME))
    if len(up_hosts) == total_num_hosts:
        return True

    # sometimes a second host is fast enough to go up without master SD, it then goes NonOperational with 5min autorecovery, let's poke it
    nonop_hosts = hosts_service.list(search='datacenter={} AND status=nonoperational'.format(DC_NAME))
    if len(nonop_hosts):
        for host in nonop_hosts:
            host_service = hosts_service.host_service(host.id)
            host_service.activate()
        return False

    _check_problematic_hosts(hosts_service)

def _single_host_up(hosts_service, total_num_hosts):
    installing_hosts = hosts_service.list(search='datacenter={} AND status=installing or status=initializing or status=connecting'.format(DC_NAME))
    if len(installing_hosts) == total_num_hosts : # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(DC_NAME))
    if len(up_hosts):
        return True

    _check_problematic_hosts(hosts_service)

def _check_problematic_hosts(hosts_service):
    problematic_hosts = hosts_service.list(search='datacenter={} AND status != installing and status != initializing and status != up'.format(DC_NAME))
    if len(problematic_hosts):
        dump_hosts = '%s hosts failed installation:\n' % len(problematic_hosts)
        for host in problematic_hosts:
            host_service = hosts_service.host_service(host.id)
            dump_hosts += '%s: %s\n' % (host.name, host_service.get().status)
        raise RuntimeError(dump_hosts)


def _host_status_to_print(hosts_service, hosts_list):
    dump_hosts = ''
    for host in hosts_list:
            host_service_info = hosts_service.host_service(host.id)
            dump_hosts += '%s: %s\n' % (host.name, host_service_info.get().status)
    return dump_hosts

def _wait_for_status(hosts_service, dc_name, status):
    up_status_seen = False
    for _ in general_utils.linear_retrier(attempts=12, iteration_sleeptime=10):
        all_hosts = hosts_service.list(search='datacenter={}'.format(dc_name))
        up_hosts = [host for host in all_hosts if host.status == status]
        LOGGER.info(_host_status_to_print(hosts_service, all_hosts))
        # we use up_status_seen because we make sure the status is not flapping
        if up_hosts:
            if up_status_seen:
                break
            up_status_seen = True
        else:
            up_status_seen = False
    return all_hosts


@pytest.mark.parametrize("key_format, verification_fn", [
    pytest.param(
        'X509-PEM-CA',
        lambda path: shell.shell(["openssl", "x509", "-in", path, "-text", "-noout"]),
        id="CA certificate"
    ),
    pytest.param(
        'OPENSSH-PUBKEY',
        lambda path: shell.shell(["ssh-keygen", "-l", "-f", path]),
        id="ssh pubkey"
    ),
])
@order_by(_TEST_LIST)
def test_verify_engine_certs(key_format, verification_fn, engine_fqdn,
                             engine_download):
    url = 'http://{}/ovirt-engine/services/pki-resource?resource=ca-certificate&format={}'

    with http_proxy_disabled(), tempfile.NamedTemporaryFile() as tmp:
        engine_download(url.format(engine_fqdn, key_format), tmp.name)
        try:
            verification_fn(tmp.name)
        except shell.ShellError:
            print("Certificate verification failed. Certificate contents:\n")
            print(tmp.read())
            raise


@pytest.mark.parametrize("scheme", ["http", "https"])
@order_by(_TEST_LIST)
def test_engine_health_status(scheme, engine_fqdn, engine_download):
    url = '{}://{}/ovirt-engine/services/health'.format(scheme, engine_fqdn)

    with http_proxy_disabled():
        assert engine_download(url) == b"DB Up!Welcome to Health Status!"


@order_by(_TEST_LIST)
def test_add_dc(engine_api):
    engine = engine_api.system_service()
    dcs_service = engine.data_centers_service()
    with test_utils.TestEvent(engine, 950): # USER_ADD_STORAGE_POOL
        assert dcs_service.add(
            sdk4.types.DataCenter(
                name=DC_NAME,
                description='APIv4 DC',
                local=False,
                version=sdk4.types.Version(major=DC_VER_MAJ,minor=DC_VER_MIN),
            ),
        )


@order_by(_TEST_LIST)
def test_remove_default_dc(engine_api):
    engine = engine_api.system_service()
    dc_service = test_utils.data_center_service(engine, 'Default')
    with test_utils.TestEvent(engine, 954): # USER_REMOVE_STORAGE_POOL event
        dc_service.remove()


@order_by(_TEST_LIST)
def test_update_default_dc(engine_api):
    engine = engine_api.system_service()
    dc_service = test_utils.data_center_service(engine, 'Default')
    with test_utils.TestEvent(engine, 952): # USER_UPDATE_STORAGE_POOL event
        dc_service.update(
            data_center=sdk4.types.DataCenter(
                local=True
            )
        )


@order_by(_TEST_LIST)
def test_update_default_cluster(engine_api):
    engine = engine_api.system_service()
    cluster_service = test_utils.get_cluster_service(engine, 'Default')
    with test_utils.TestEvent(engine, 811): # USER_UPDATE_CLUSTER event
        cluster_service.update(
            cluster=sdk4.types.Cluster(
                cpu=sdk4.types.Cpu(
                    architecture=sdk4.types.Architecture.PPC64
                )
            )
        )


@order_by(_TEST_LIST)
def test_remove_default_cluster(engine_api):
    engine = engine_api.system_service()
    cl_service = test_utils.get_cluster_service(engine, 'Default')
    with test_utils.TestEvent(engine, 813): # USER_REMOVE_CLUSTER event
        cl_service.remove()


@order_by(_TEST_LIST)
def test_add_dc_quota(engine_api):
    datacenters_service = engine_api.system_service().data_centers_service()
    datacenter = datacenters_service.list(search='name=%s' % DC_NAME)[0]
    datacenter_service = datacenters_service.data_center_service(datacenter.id)
    quotas_service = datacenter_service.quotas_service()
    assert quotas_service.add(
        types.Quota (
            name=DC_QUOTA_NAME,
            description='DC-QUOTA-DESCRIPTION',
            data_center=datacenter,
            cluster_soft_limit_pct=99
        )
    )

@order_by(_TEST_LIST)
def test_add_cluster(engine_api):
    engine = engine_api.system_service()
    clusters_service = engine.clusters_service()
    provider_id = network_utils_v4.get_default_ovn_provider_id(engine)
    with test_utils.TestEvent(engine, 809):
        assert clusters_service.add(
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


@order_by(_TEST_LIST)
def test_sync_time(ansible_hosts, engine_hostname):
    ansible_hosts.shell('chronyc -4 add server {}'.format(engine_hostname))
    ansible_hosts.shell('chronyc -4 makestep')


@order_by(_TEST_LIST)
def test_add_hosts(ansible_host0_facts, ansible_host1_facts, engine_api,
                   root_password):
    engine = engine_api.system_service()

    hostnames = [
        facts.get("ansible_hostname")
        for facts in [ansible_host0_facts, ansible_host1_facts]
    ]

    def _add_host(hostname):
        return engine.hosts_service().add(
            sdk4.types.Host(
                name=hostname,
                description='host %s' % hostname,
                address=hostname,
                root_password=root_password,
                override_iptables=True,
                cluster=sdk4.types.Cluster(
                    name=CLUSTER_NAME,
                ),
            ),
        )

    with test_utils.TestEvent(engine, 42):
        for hostname in hostnames:
            assert _add_host(hostname)


@order_by(_TEST_LIST)
def test_verify_add_hosts(engine_api):
    hosts_service = engine_api.system_service().hosts_service()
    hosts_status = hosts_service.list(search='datacenter={}'.format(DC_NAME))
    total_hosts = len(hosts_status)
    dump_hosts = _host_status_to_print(hosts_service, hosts_status)
    LOGGER.debug('Host status, verify_add_hosts:\n {}'.format(dump_hosts))
    testlib.assert_true_within(
        lambda: _single_host_up(hosts_service, total_hosts),
        timeout=constants.ADD_HOST_TIMEOUT
    )

@order_by(_TEST_LIST)
def test_verify_add_all_hosts(engine_api):
    hosts_service = engine_api.system_service().hosts_service()
    total_hosts = len(hosts_service.list(search='datacenter={}'.format(DC_NAME)))

    testlib.assert_true_within(
        lambda: _all_hosts_up(hosts_service, total_hosts),
        timeout=constants.ADD_HOST_TIMEOUT
    )


@order_by(_TEST_LIST)
def test_complete_hosts_setup(ansible_hosts):
    if not os.environ.get('ENABLE_DEBUG_LOGGING'):
        pytest.skip('Skip vdsm debug logging')

    ansible_hosts.shell('vdsm-client Host setLogLevel level=DEBUG')

    loggers = (
        ('root', 'root'),
        ('vds', 'vds'),
        ('virt', 'virt'),
        ('schema_inconsistency', 'schema.inconsistency')
    )

    for name, qualified_name in loggers:
        ansible_hosts.shell(
            'vdsm-client Host setLogLevel level=DEBUG name={}'.format(qualified_name)
        )
        sed_expr = '/logger_{}/,/level=/s/level=INFO/level=DEBUG/'.format(name)
        ansible_hosts.shell(
            'sed -i {} /etc/vdsm/logger.conf'.format(sed_expr)
        )


@pytest.fixture(scope="session")
def sd_iscsi_port():
    return SD_ISCSI_PORT


@pytest.fixture(scope="session")
def sd_iscsi_target():
    return SD_ISCSI_TARGET


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host(ansible_engine):
    return ansible_engine


@pytest.fixture(scope="session")
def sd_iscsi_host_ips(engine_storage_ips):
    return engine_storage_ips


@pytest.fixture
def sd_iscsi_host_lun_uuids(sd_iscsi_ansible_host):
    return lun.get_uuids(sd_iscsi_ansible_host)[:SD_ISCSI_NR_LUNS]


@pytest.fixture
def sd_iscsi_host_luns(sd_iscsi_host_lun_uuids, sd_iscsi_host_ips,
                       sd_iscsi_port, sd_iscsi_target):
    return lun.create_lun_sdk_entries(sd_iscsi_host_lun_uuids,
                                      sd_iscsi_host_ips, sd_iscsi_port,
                                      sd_iscsi_target)


@order_by(_TEST_LIST)
@pytest.mark.skipif(MASTER_SD_TYPE != 'iscsi', reason='not using iscsi')
def test_add_iscsi_master_storage_domain(engine_api, sd_iscsi_host_luns):
    add_iscsi_storage_domain(engine_api, sd_iscsi_host_luns)


@pytest.fixture(scope="session")
def sd_nfs_host_storage_ip(engine_storage_ips):
    return engine_storage_ips[0]


@order_by(_TEST_LIST)
@pytest.mark.skipif(MASTER_SD_TYPE != 'nfs', reason='not using nfs')
def test_add_nfs_master_storage_domain(engine_api, sd_nfs_host_storage_ip):
    add_nfs_storage_domain(engine_api, sd_nfs_host_storage_ip)


def add_nfs_storage_domain(engine_api, sd_nfs_host_storage_ip):
    random_host = _random_host_from_dc(engine_api, DC_NAME)
    LOGGER.debug('random host: {}'.format(random_host.name))

    nfs.add_domain(engine_api, SD_NFS_NAME, random_host,
                   sd_nfs_host_storage_ip, SD_NFS_PATH, DC_NAME,
                   nfs_version='v4_2')


# TODO: add this over the storage network and with IPv6
def add_second_nfs_storage_domain(engine_api, sd_nfs_host_storage_ip):
    random_host = _random_host_from_dc(engine_api, DC_NAME)
    LOGGER.debug('random host: {}'.format(random_host.name))

    nfs.add_domain(engine_api, SD_SECOND_NFS_NAME, random_host,
                   sd_nfs_host_storage_ip, SD_SECOND_NFS_PATH, DC_NAME)


@order_by(_TEST_LIST)
def test_add_secondary_storage_domains(engine_api, sd_nfs_host_storage_ip,
                                       sd_iscsi_host_luns):
    if MASTER_SD_TYPE == 'iscsi':
        vt = utils.VectorThread(
            [
                functools.partial(add_nfs_storage_domain, engine_api,
                                  sd_nfs_host_storage_ip),
# 12/07/2017 commenting out iso domain creation until we know why it causing random failures
# Bug-Url: http://bugzilla.redhat.com/1463263
#                functools.partial(add_iso_storage_domain, engine_api,
#                                  sd_nfs_host_storage_ip),
                functools.partial(add_templates_storage_domain, engine_api,
                                  sd_nfs_host_storage_ip),
                functools.partial(add_second_nfs_storage_domain, engine_api,
                                  sd_nfs_host_storage_ip),

            ],
        )
    else:
        vt = utils.VectorThread(
            [
                functools.partial(add_iscsi_storage_domain, engine_api,
                                  sd_iscsi_host_luns),
# 12/07/2017 commenting out iso domain creation until we know why it causing random failures
#Bug-Url: http://bugzilla.redhat.com/1463263
#                functools.partial(add_iso_storage_domain, engine_api,
#                                  sd_nfs_host_storage_ip),
                functools.partial(add_templates_storage_domain, engine_api,
                                  sd_nfs_host_storage_ip),
                functools.partial(add_second_nfs_storage_domain, engine_api,
                                  sd_nfs_host_storage_ip),

            ],
        )
    vt.start_all()
    vt.join_all()


@order_by(_TEST_LIST)
def test_resize_and_refresh_storage_domain(sd_iscsi_ansible_host, engine_api,
                                           sd_iscsi_host_luns):
    sd_iscsi_ansible_host.shell(
        'lvresize --size +3000M /dev/mapper/vg1_storage-lun0_bdev'
    )

    engine = engine_api.system_service()
    storage_domain_service = test_utils.get_storage_domain_service(engine, SD_ISCSI_NAME)

    with test_utils.TestEvent(engine, 1022): # USER_REFRESH_LUN_STORAGE_DOMAIN(1,022)
        storage_domain_service.refresh_luns(
            async=False,
            logical_units=sd_iscsi_host_luns
        )


@order_by(_TEST_LIST)
def test_add_glance_images(engine_api):
    system_service = engine_api.system_service()
    non_template_import = functools.partial(
        glance.import_image, system_service,
        GUEST_IMAGE_NAME, TEMPLATE_GUEST, GLANCE_DISK_NAME,
        MASTER_SD_TYPE, CLUSTER_NAME, SD_GLANCE_NAME
    )
    template_import = functools.partial(
        glance.import_image, system_service,
        GUEST_IMAGE_NAME, TEMPLATE_GUEST, TEMPLATE_GUEST,
        MASTER_SD_TYPE, CLUSTER_NAME, SD_GLANCE_NAME, as_template=True
    )
    vt = utils.VectorThread(
        [
            non_template_import,
            template_import,
        ],
    )
    vt.start_all()
    vt.join_all()


def add_iscsi_storage_domain(engine_api, luns):
    v4_domain = versioning.cluster_version_ok(4, 1)
    p = sdk4.types.StorageDomain(
        name=SD_ISCSI_NAME,
        description='iSCSI Storage Domain',
        type=sdk4.types.StorageDomainType.DATA,
        discard_after_delete=v4_domain,
        data_center=sdk4.types.DataCenter(
            name=DC_NAME,
        ),
        host=_random_host_from_dc(engine_api, DC_NAME),
        storage_format=(sdk4.types.StorageFormat.V4 if v4_domain else sdk4.types.StorageFormat.V3),
        storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.ISCSI,
            override_luns=True,
            volume_group=sdk4.types.VolumeGroup(
                logical_units=luns
            ),
        ),
    )

    domain.add(engine_api, p, DC_NAME)


def add_iso_storage_domain(engine_api, sd_host_storage_ip):
    random_host = _random_host_from_dc(engine_api, DC_NAME)
    LOGGER.debug('random host: {}'.format(random_host.name))

    nfs.add_domain(engine_api, SD_ISO_NAME, random_host, sd_host_storage_ip,
                   SD_ISO_PATH, DC_NAME, sd_format='v1', sd_type='iso',
                   nfs_version='v3')


def add_templates_storage_domain(engine_api, sd_host_storage_ip):
    random_host = _random_host_from_dc(engine_api, DC_NAME)
    LOGGER.debug('random host: {}'.format(random_host.name))

    nfs.add_domain(engine_api, SD_TEMPLATES_NAME, random_host,
                   sd_host_storage_ip, SD_TEMPLATES_PATH, DC_NAME,
                   sd_format='v1', sd_type='export', nfs_version='v4_1')


@order_by(_TEST_LIST)
def test_list_glance_images(engine_api):
    search_query = 'name={}'.format(SD_GLANCE_NAME)
    system_service = engine_api.system_service()
    storage_domains_service = system_service.storage_domains_service()
    glance_domain_list = storage_domains_service.list(search=search_query)

    if not glance_domain_list:
        openstack_glance = glance.add_domain(system_service, SD_GLANCE_NAME,
                                             GLANCE_SERVER_URL)
        if not openstack_glance:
            raise RuntimeError('GLANCE storage domain is not available.')
        glance_domain_list = storage_domains_service.list(search=search_query)

    if not glance.check_connectivity(system_service, SD_GLANCE_NAME):
        raise RuntimeError('GLANCE connectivity test failed')

    glance_domain = glance_domain_list.pop()
    glance_domain_service = storage_domains_service.storage_domain_service(
        glance_domain.id
    )

    try:
        with test_utils.TestEvent(system_service, 998):
            all_images = glance_domain_service.images_service().list()
        if not len(all_images):
            raise RuntimeError('No GLANCE images available')
    except sdk4.Error:
        raise RuntimeError('GLANCE is not available: client request error')


@order_by(_TEST_LIST)
def test_set_dc_quota_audit(engine_api):
    dcs_service = engine_api.system_service().data_centers_service()
    dc = dcs_service.list(search='name=%s' % DC_NAME)[0]
    dc_service = dcs_service.data_center_service(dc.id)
    assert dc_service.update(
        types.DataCenter(
            quota_mode=types.QuotaModeType.AUDIT,
        ),
    )


@order_by(_TEST_LIST)
def test_add_quota_storage_limits(engine_api):

    # Find the data center and the service that manages it:
    dcs_service = engine_api.system_service().data_centers_service()
    dc = dcs_service.list(search='name=%s' % DC_NAME)[0]
    dc_service = dcs_service.data_center_service(dc.id)

    # Find the storage domain and the service that manages it:
    sds_service = engine_api.system_service().storage_domains_service()
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
    assert limits_service.add(
        limit=types.QuotaStorageLimit(
            limit=500,
        )
    )

@order_by(_TEST_LIST)
def test_add_quota_cluster_limits(engine_api):
    datacenters_service = engine_api.system_service().data_centers_service()
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
    assert quota_cluster_limits_service.add(
        types.QuotaClusterLimit(
            vcpu_limit=20,
            memory_limit=10000.0
        )
    )

@order_by(_TEST_LIST)
def test_add_vm_network(engine_api):
    engine = engine_api.system_service()

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
        assert engine.networks_service().add(network)

    cluster_service = test_utils.get_cluster_service(engine, CLUSTER_NAME)
    assert cluster_service.networks_service().add(network)


@order_by(_TEST_LIST)
def test_add_non_vm_network(engine_api):
    engine = engine_api.system_service()

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
        assert engine.networks_service().add(network)

    cluster_service = test_utils.get_cluster_service(engine, CLUSTER_NAME)
    assert cluster_service.networks_service().add(network)


@order_by(_TEST_LIST)
def test_add_role(engine_api):
    engine = engine_api.system_service()
    roles_service = engine.roles_service()
    with test_utils.TestEvent(engine, 864): # USER_ADD_ROLE_WITH_ACTION_GROUP event
        assert roles_service.add(
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


@order_by(_TEST_LIST)
def test_add_affinity_label(engine_api):
    engine = engine_api.system_service()
    affinity_labels_service = engine.affinity_labels_service()
    with test_utils.TestEvent(engine, 10380):
        assert affinity_labels_service.add(
            sdk4.types.AffinityLabel(
                name='my_affinity_label',
            ),
        )


@order_by(_TEST_LIST)
def test_add_affinity_group(engine_api):
    engine = engine_api.system_service()
    cluster_service = test_utils.get_cluster_service(engine, CLUSTER_NAME)
    affinity_group_service = cluster_service.affinity_groups_service()
    with test_utils.TestEvent(engine, 10350):
        assert affinity_group_service.add(
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


@order_by(_TEST_LIST)
def test_add_bookmark(engine_api):
    engine = engine_api.system_service()
    bookmarks_service = engine.bookmarks_service()
    with test_utils.TestEvent(engine, 350):
        assert bookmarks_service.add(
            sdk4.types.Bookmark(
                name='my_bookmark',
                value='vm:name=vm*',
            ),
        )


@order_by(_TEST_LIST)
def test_add_cpu_profile(engine_api):
    engine = engine_api.system_service()
    cpu_profiles_service = engine.cpu_profiles_service()
    cluster_service = test_utils.get_cluster_service(engine, CLUSTER_NAME)
    with test_utils.TestEvent(engine, 10130): # USER_ADDED_CPU_PROFILE event
        assert cpu_profiles_service.add(
            sdk4.types.CpuProfile(
                name='my_cpu_profile',
                cluster=sdk4.types.Cluster(
                    id=cluster_service.get().id,
                ),
            ),
        )


@order_by(_TEST_LIST)
def test_add_qos(engine_api):
    engine = engine_api.system_service()
    dc_service = test_utils.data_center_service(engine, DC_NAME)
    qoss = dc_service.qoss_service()
    with test_utils.TestEvent(engine, 10110): # USER_ADDED_QOS event
        assert qoss.add(
            sdk4.types.Qos(
                name='my_cpu_qos',
                type=sdk4.types.QosType.CPU,
                cpu_limit=99,
            ),
        )
    with test_utils.TestEvent(engine, 10110): # USER_ADDED_QOS event
        assert qoss.add(
            sdk4.types.Qos(
                name='my_storage_qos',
                type=sdk4.types.QosType.STORAGE,
                max_iops=999999,
                description='max_iops_qos',
            ),
        )


@order_by(_TEST_LIST)
def test_add_disk_profile(engine_api):
    engine = engine_api.system_service()
    disk_profiles_service = engine.disk_profiles_service()
    dc_service = test_utils.data_center_service(engine, DC_NAME)
    attached_sds_service = dc_service.storage_domains_service()
    attached_sd = attached_sds_service.list()[0]

    with test_utils.TestEvent(engine, 10120): # USER_ADDED_DISK_PROFILE event
        assert disk_profiles_service.add(
            sdk4.types.DiskProfile(
                name='my_disk_profile',
                storage_domain=sdk4.types.StorageDomain(
                    id=attached_sd.id,
                ),
            ),
        )


@order_by(_TEST_LIST)
def test_get_version(engine_api):
    product_info = engine_api.system_service().get().product_info
    name = product_info.name
    major_version = product_info.version.major
    assert name in ('oVirt Engine', 'Red Hat Virtualization Manager')
    assert major_version == 4


@order_by(_TEST_LIST)
def test_get_cluster_enabled_features(engine_api):
    cluster_service = test_utils.get_cluster_service(engine_api.system_service(), CLUSTER_NAME)
    enabled_features_service = cluster_service.enabled_features_service()
    features = sorted(enabled_features_service.list(), key=lambda feature: feature.name)
    #TODO: Fix the below - why is features null?
    pytest.skip('skipping - features is []')
    feature_list = ''
    for feature in features:
        if feature.name == 'XYZ':
            return True
        else:
            feature_list += (feature.name + '; ')
    raise RuntimeError('Feature XYZ is not in cluster enabled features: {0}'.format(feature_list))


@order_by(_TEST_LIST)
def test_get_cluster_levels(engine_api):
    cluster_levels_service = engine_api.system_service().cluster_levels_service()
    cluster_levels = sorted(cluster_levels_service.list(), key=lambda level:level.id)
    assert cluster_levels
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


@order_by(_TEST_LIST)
def test_get_domains(engine_api):
    domains_service = engine_api.system_service().domains_service()
    domains = sorted(domains_service.list(), key=lambda domain: domain.name)
    for domain in domains:
        if domain.name == 'internal-authz':
            return True
    raise RuntimeError('Could not find internal-authz domain in domains list')


@order_by(_TEST_LIST)
def test_get_host_devices(engine_api):
    host_service = _random_host_service_from_dc(engine_api, DC_NAME)
    for i in range(10):
        devices_service = host_service.devices_service()
        devices = sorted(devices_service.list(), key=lambda device: device.name)
        device_list = ''
        for device in devices:
            if device.name == 'block_vda_1': # first virtio-blk disk
                return True
            else:
                device_list += (device.name + '; ')
        time.sleep(1)
    raise RuntimeError('Could not find block_vda_1 device in host devices: {}'.format(device_list))


@order_by(_TEST_LIST)
def test_get_host_hooks(engine_api):
    host_service = _random_host_service_from_dc(engine_api, DC_NAME)
    hooks_service = host_service.hooks_service()
    hooks = sorted(hooks_service.list(), key=lambda hook: hook.name)
    hooks_list = ''
    for hook in hooks:
        if hook.name == '50_vhostmd':
            return True
        else:
            hooks_list += (hook.name + '; ')
    raise RuntimeError('could not find 50_vhostmd hook in host hooks: {0}'.format(hooks_list))


@order_by(_TEST_LIST)
def test_get_host_stats(engine_api):
    host_service = _random_host_service_from_dc(engine_api, DC_NAME)
    stats_service = host_service.statistics_service()
    stats = sorted(stats_service.list(), key=lambda stat: stat.name)
    stats_list = ''
    for stat in stats:
        if stat.name == 'boot.time':
            return True
        else:
            stats_list += (stat.name + '; ')
    raise RuntimeError('boot.time stat not in stats: {0}'.format(stats_list))


@order_by(_TEST_LIST)
def test_get_host_numa_nodes(engine_api):
    host_service = _random_host_service_from_dc(engine_api, DC_NAME)
    numa_nodes_service = host_service.numa_nodes_service()
    nodes = sorted(numa_nodes_service.list(), key=lambda node: node.index)
    # TODO: Do a better check on the result nodes struct.
    # The below is too simplistic.
    pytest.skip(' [2018-02-08] test itself identified as possibly faulty')
    assert nodes[0].index == 0
    assert len(nodes) > 1


@order_by(_TEST_LIST)
def test_check_update_host(engine_api):
    engine = engine_api.system_service()
    host_service = _random_host_service_from_dc(engine_api, DC_NAME)
    events_service = engine.events_service()
    with test_utils.TestEvent(engine, [884, 885]):
        # HOST_AVAILABLE_UPDATES_STARTED(884)
        # HOST_AVAILABLE_UPDATES_FINISHED(885)
        host_service.upgrade_check()


@order_by(_TEST_LIST)
def test_add_scheduling_policy(engine_api):
    engine = engine_api.system_service()
    scheduling_policies_service = engine.scheduling_policies_service()
    with test_utils.TestEvent(engine, 9910):
        assert scheduling_policies_service.add(
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


@order_by(_TEST_LIST)
def test_get_system_options(engine_api):
    #TODO: get some option
    options_service = engine_api.system_service().options_service()


@order_by(_TEST_LIST)
def test_get_operating_systems(engine_api):
    operating_systems_service = engine_api.system_service().operating_systems_service()
    os_list = sorted(operating_systems_service.list(), key=lambda os:os.name)
    assert os_list
    os_string = ''
    for os in os_list:
        if os.name == 'rhel_7x64':
            return True
        else:
            os_string += (os.name + '; ')
    raise RuntimeError('Could not find rhel_7x64 in operating systems list: {0}'.format(os_string))


@order_by(_TEST_LIST)
def test_add_fence_agent(engine_api):
    # TODO: This just adds a fence agent to host, does not enable it.
    # Of course, we need to find a fence agents that can work on
    # VMs via the host libvirt, etc...
    host_service = _random_host_service_from_dc(engine_api, DC_NAME)

    fence_agents_service = host_service.fence_agents_service()
    pytest.skip('Enabling this may affect tests. Needs further tests')
    assert fence_agents_service.add(
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


@order_by(_TEST_LIST)
def test_add_tag(engine_api):
    engine = engine_api.system_service()
    tags_service = engine.tags_service()
    assert tags_service.add(
        sdk4.types.Tag(
            name='mytag',
            description='My custom tag',
        ),
    )


@order_by(_TEST_LIST)
def test_add_mac_pool(engine_api):
    engine = engine_api.system_service()
    pools_service = engine.mac_pools_service()
    with test_utils.TestEvent(engine, 10700): # MAC_POOL_ADD_SUCCESS event
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
        assert pool

    cluster_service = test_utils.get_cluster_service(engine, 'Default')
    with test_utils.TestEvent(engine, 811):
        assert cluster_service.update(
            cluster=sdk4.types.Cluster(
                mac_pool=sdk4.types.MacPool(
                    id=pool.id,
                )
            )
        )


@order_by(_TEST_LIST)
def test_verify_notifier(ansible_engine):
    ansible_engine.shell('grep USER_VDC_LOGIN /var/log/messages')
    ansible_engine.systemd(name='ovirt-engine-notifier', state='stopped')
    ansible_engine.systemd(name='snmptrapd', state='stopped')


@order_by(_TEST_LIST)
def test_verify_glance_import(engine_api):
    # If we go with the engine backup before the glance template
    # creation is complete, we'll fail the creation of 'vm1' later,
    # which is based on that template.
    templates_service = engine_api.system_service().templates_service()

    testlib.assert_true_within_long(
        lambda: TEMPLATE_GUEST in [t.name for t in templates_service.list()]
    )

    for disk_name in (GLANCE_DISK_NAME, TEMPLATE_GUEST):
        disks_service = engine_api.system_service().disks_service()
        testlib.assert_true_within_long(
            lambda: disks_service.list(search='name={}'.format(disk_name))[0].status == types.DiskStatus.OK
        )


@order_by(_TEST_LIST)
def test_verify_engine_backup(ansible_engine, engine_api):
    ansible_engine.file(
        path='/var/log/ost-engine-backup',
        state='directory',
        mode='0755'
    )

    engine = engine_api.system_service()

    with test_utils.TestEvent(engine, [9024, 9025]): #backup started event, completed
        ansible_engine.shell(
            'engine-backup '
            '--mode=backup '
            '--file=/var/log/ost-engine-backup/backup.tgz '
            '--log=/var/log/ost-engine-backup/log.txt'
        )

    ansible_engine.shell(
        'engine-backup '
        '--mode=verify '
        '--file=/var/log/ost-engine-backup/backup.tgz '
        '--log=/var/log/ost-engine-backup/verify-log.txt'
    )

    ansible_engine.shell(
        'engine-cleanup '
        '--otopi-environment="OVESETUP_CORE/remove=bool:True OVESETUP_CORE/engineStop=bool:True"'
    )

    ansible_engine.shell(
        'engine-backup '
        '--mode=restore '
        '--provision-all-databases '
        '--file=/var/log/ost-engine-backup/backup.tgz '
        '--log=/var/log/ost-engine-backup/verify-restore-log.txt'
    )

    ansible_engine.shell(
        'engine-setup '
        '--accept-defaults '
        '--offline '
        '--otopi-environment=OVESETUP_SYSTEM/memCheckEnabled=bool:False'
    )


@order_by(_TEST_LIST)
def test_add_vnic_passthrough_profile(engine_api):
    engine = engine_api.system_service()
    vnic_service = test_utils.get_vnic_profiles_service(engine, MANAGEMENT_NETWORK)

    with test_utils.TestEvent(engine, 1122):
        vnic_profile = vnic_service.add(
            profile=sdk4.types.VnicProfile(
                name=PASSTHROUGH_VNIC_PROFILE,
                pass_through=sdk4.types.VnicPassThrough(
                    mode=sdk4.types.VnicPassThroughMode.ENABLED
                )
            )
        )
        assert vnic_profile.pass_through.mode == sdk4.types.VnicPassThroughMode.ENABLED


@order_by(_TEST_LIST)
def test_remove_vnic_passthrough_profile(engine_api):
    engine = engine_api.system_service()
    vnic_service = test_utils.get_vnic_profiles_service(engine, MANAGEMENT_NETWORK)

    vnic_profile = next(vnic_profile for vnic_profile in vnic_service.list()
                        if vnic_profile.name == PASSTHROUGH_VNIC_PROFILE
                        )

    with test_utils.TestEvent(engine, 1126):
        vnic_service.profile_service(vnic_profile.id).remove()
        assert next((vp for vp in vnic_service.list()
                     if vp.name == PASSTHROUGH_VNIC_PROFILE), None) is None


@order_by(_TEST_LIST)
def test_add_blank_vms(engine_api):
    engine = engine_api.system_service()
    vms_service = engine.vms_service()

    vm_params = sdk4.types.Vm(
        os=sdk4.types.OperatingSystem(
            type='other_linux',
        ),
        type=sdk4.types.VmType.SERVER,
        high_availability=sdk4.types.HighAvailability(
            enabled=False,
        ),
        cluster=sdk4.types.Cluster(
            name=CLUSTER_NAME,
        ),
        template=sdk4.types.Template(
            name=TEMPLATE_BLANK,
        ),
        display=sdk4.types.Display(
            # TODO: Enable smartcard again once
            # https://bugzilla.redhat.com/1876635 is resolved.
            smartcard_enabled=False,
            keyboard_layout='en-us',
            file_transfer_enabled=True,
            copy_paste_enabled=True,
        ),
        usb=sdk4.types.Usb(
            enabled=True,
            type=sdk4.types.UsbType.NATIVE,
        ),
        memory_policy=sdk4.types.MemoryPolicy(
            ballooning=True,
        ),
    )

    vm_params.name = BACKUP_VM_NAME
    vm_params.memory = 96 * MB
    vm_params.memory_policy.guaranteed = 64 * MB
    vms_service.add(vm_params)
    backup_vm_service = test_utils.get_vm_service(engine, BACKUP_VM_NAME)

    vm_params.name = VM0_NAME
    least_hotplug_increment = 256 * MB
    required_memory = 96 * MB
    vm_params.memory = required_memory
    vm_params.memory_policy.guaranteed = required_memory
    vm_params.memory_policy.max = required_memory + least_hotplug_increment

    vms_service.add(vm_params)
    vm0_vm_service = test_utils.get_vm_service(engine, VM0_NAME)

    for vm_service in [backup_vm_service, vm0_vm_service]:
        testlib.assert_true_within_short(
            lambda:
            vm_service.get().status == sdk4.types.VmStatus.DOWN
        )


@order_by(_TEST_LIST)
def test_add_blank_high_perf_vm2(engine_api):
    engine = engine_api.system_service()
    hosts_service = engine.hosts_service()
    hosts = hosts_service.list(search='datacenter={} AND status=up'.format(DC_NAME))

    vms_service = engine.vms_service()
    vms_service.add(
        sdk4.types.Vm(
            name=VM2_NAME,
            description='Mostly complete High-Performance VM configuration',
            cluster=sdk4.types.Cluster(
            name=CLUSTER_NAME,
            ),
            template=sdk4.types.Template(
                name=TEMPLATE_BLANK,
            ),
            custom_emulated_machine = 'pc-q35-rhel8.0.0',
            cpu=sdk4.types.Cpu(
                topology=sdk4.types.CpuTopology(
                    cores=1,
                    sockets=2,
                    threads=1,
                ),
                mode=sdk4.types.CpuMode.HOST_PASSTHROUGH,
                cpu_tune=sdk4.types.CpuTune(
                    vcpu_pins=[
                        sdk4.types.VcpuPin(
                            cpu_set='0',
                            vcpu=0,
                        ),
                        sdk4.types.VcpuPin(
                            cpu_set='1',
                            vcpu=1,
                        ),
                    ],
                ),
            ),
            usb=sdk4.types.Usb(
                enabled=False,
                type=sdk4.types.UsbType.NATIVE,
            ),
            soundcard_enabled=False,
            display=sdk4.types.Display(
                smartcard_enabled=False,
                file_transfer_enabled=False,
                copy_paste_enabled=False,
                type=sdk4.types.DisplayType.SPICE,
            ),
            os=sdk4.types.OperatingSystem(
                type='Linux',
            ),
            io=sdk4.types.Io(
                threads=1,
            ),
            memory_policy=sdk4.types.MemoryPolicy(
                ballooning=False,
                guaranteed=64 * MB,
                max=256 * MB,
            ),
            memory=96 * MB,
            high_availability=sdk4.types.HighAvailability(
                enabled=True,
                priority=100,
            ),
            rng_device=sdk4.types.RngDevice(
                source=sdk4.types.RngSource.URANDOM,
            ),
            placement_policy=sdk4.types.VmPlacementPolicy(
                affinity=sdk4.types.VmAffinity.PINNED,
                hosts=hosts,
            ),
            numa_tune_mode=sdk4.types.NumaTuneMode.INTERLEAVE,
            type=(sdk4.types.VmType.HIGH_PERFORMANCE
                  if versioning.cluster_version_ok(4, 2) else
                  sdk4.types.VmType.SERVER),
            custom_properties=[
                sdk4.types.CustomProperty(
                    name='viodiskcache',
                    value='writethrough',
                ),
            ],
        ),
    )
    vm2_service = test_utils.get_vm_service(engine, VM2_NAME)
    testlib.assert_true_within_long(
        lambda:
        vm2_service.get().status == sdk4.types.VmStatus.DOWN
    )


@order_by(_TEST_LIST)
def test_configure_high_perf_vm2(engine_api):
    engine = engine_api.system_service()
    vm2_service = test_utils.get_vm_service(engine, VM2_NAME)
    vm2_graphics_consoles_service = vm2_service.graphics_consoles_service()
    vm2_graphics_consoles = vm2_graphics_consoles_service.list()
    for graphics_console in vm2_graphics_consoles:
        console_service = vm2_graphics_consoles_service.console_service(graphics_console.id)
        console_service.remove()

    vm2_numanodes_service = vm2_service.numa_nodes_service()
    topology = vm2_service.get().cpu.topology
    total_vcpus = topology.sockets * topology.cores * topology.threads
    total_memory = vm2_service.get().memory // MB
    pytest.skip('Skipping until vNUMA and pinning to hosts work together')
    for i in range(total_vcpus):
        assert vm2_numanodes_service.add(
            node=sdk4.types.VirtualNumaNode(
                index=i,
                name='{0} vnuma node {1}'.format(VM2_NAME, i),
                memory= total_memory // total_vcpus,
                cpu=sdk4.types.Cpu(
                    cores=[
                        sdk4.types.Core(
                            index=i,
                        ),
                    ],
                ),
                numa_node_pins=[
                    sdk4.types.NumaNodePin(
                        index=i,
                    ),
                ],
            )
        )

    assert len(vm2_service.numa_nodes_service().list()) == total_vcpus


@versioning.require_version(4, 1)
@order_by(_TEST_LIST)
def test_add_vm2_lease(engine_api):
    engine = engine_api.system_service()
    vm2_service = test_utils.get_vm_service(engine, VM2_NAME)
    sd = engine.storage_domains_service().list(search='name={}'.format(SD_SECOND_NFS_NAME))[0]

    vm2_service.update(
        vm=sdk4.types.Vm(
            high_availability=sdk4.types.HighAvailability(
                enabled=True,
            ),
            lease=sdk4.types.StorageDomainLease(
                storage_domain=sdk4.types.StorageDomain(
                    id=sd.id
                )
            )
        )
    )
    testlib.assert_true_within_short(
        lambda:
        vm2_service.get().lease.storage_domain.id == sd.id
    )


@order_by(_TEST_LIST)
def test_add_nic(engine_api):
    NIC_NAME = 'eth0'
    # Locate the vnic profiles service and use it to find the ovirmgmt
    # network's profile id:
    profiles_service = engine_api.system_service().vnic_profiles_service()
    profile_id = next(
        (
            profile.id for profile in profiles_service.list()
            if profile.name == MANAGEMENT_NETWORK
        ),
        None
    )

    # Empty profile id would cause fail in later tests (e.g. add_filter):
    assert profile_id is not None

    # Locate the virtual machines service and use it to find the virtual
    # machine:
    vms_service = engine_api.system_service().vms_service()
    vm = vms_service.list(search='name=%s' % VM0_NAME)[0]

    # Locate the service that manages the network interface cards of the
    # virtual machine:
    nics_service = vms_service.vm_service(vm.id).nics_service()

    # Use the "add" method of the network interface cards service to add the
    # new network interface card:
    nics_service.add(
        types.Nic(
            name=NIC_NAME,
            interface=types.NicInterface.VIRTIO,
            vnic_profile=types.VnicProfile(
                id=profile_id
            ),
        ),
    )

    vm = vms_service.list(search='name=%s' % VM2_NAME)[0]
    nics_service = vms_service.vm_service(vm.id).nics_service()
    nics_service.add(
        types.Nic(
            name=NIC_NAME,
            interface=types.NicInterface.E1000,
            mac=types.Mac(address=UNICAST_MAC_OUTSIDE_POOL),
            vnic_profile=types.VnicProfile(
                id=profile_id
            ),
        ),
    )


@order_by(_TEST_LIST)
def test_add_graphics_console(engine_api):
    # remove VNC
    engine = engine_api.system_service()
    vm = test_utils.get_vm_service(engine, VM0_NAME)
    consoles_service = vm.graphics_consoles_service()
    if len(consoles_service.list()) == 2:
        console = consoles_service.console_service('766e63')
        console.remove()
        testlib.assert_true_within_short(
            lambda:
            len(consoles_service.list()) == 1
        )

    # and add it back
    consoles_service.add(
        sdk4.types.GraphicsConsole(
            protocol=sdk4.types.GraphicsType.VNC,
        )
    )
    testlib.assert_true_within_short(
        lambda:
        len(consoles_service.list()) == 2
    )


@order_by(_TEST_LIST)
def test_add_filter(engine_api):
    engine = engine_api.system_service()
    nics_service = test_utils.get_nics_service(engine, VM0_NAME)
    nic = nics_service.list()[0]
    network = engine_api.follow_link(nic.vnic_profile).network
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
    assert nics_service.nic_service(nic.id).update(nic)


@order_by(_TEST_LIST)
def test_add_filter_parameter(engine_api, engine_ip):
    vm_gw = '.'.join(engine_ip.split('.')[0:3] + ['1'])
    engine = engine_api.system_service()
    network_filter_parameters_service = test_utils.get_network_fiter_parameters_service(
        engine, VM0_NAME)

    with test_utils.TestEvent(engine, 10912):
        assert network_filter_parameters_service.add(
            sdk4.types.NetworkFilterParameter(
                name='GW_IP',
                value=vm_gw
            )
        )


@order_by(_TEST_LIST)
def test_add_serial_console_vm2(engine_api):
    engine = engine_api.system_service()
    # Find the virtual machine. Note the use of the `all_content` parameter, it is
    # required in order to obtain additional information that isn't retrieved by
    # default, like the configuration of the serial console.
    vm = engine.vms_service().list(search='name={}'.format(VM2_NAME), all_content=True)[0]
    if not vm.console.enabled:
        vm_service = test_utils.get_vm_service(engine, VM2_NAME)
        with test_utils.TestEvent(engine, 35): # USER_UPDATE_VM event
            vm_service.update(
                sdk4.types.Vm(
                    console=sdk4.types.Console(
                        enabled=True
                    )
                )
            )


@order_by(_TEST_LIST)
def test_add_instance_type(engine_api):
    engine = engine_api.system_service()
    instance_types_service = engine.instance_types_service()
    with test_utils.TestEvent(engine, 29):
        assert instance_types_service.add(
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


@order_by(_TEST_LIST)
def test_add_event(engine_api):
    events_service = engine_api.system_service().events_service()
    assert events_service.add( # Add a new event to the system
        types.Event(
            description='ovirt-system-tests description',
            custom_id=int('01234567890'),
            severity=types.LogSeverity.NORMAL,
            origin='ovirt-system-tests',
            cluster=types.Cluster(
                name=CLUSTER_NAME,
            )
        ),
    )


@order_by(_TEST_LIST)
def test_add_direct_lun_vm0(prefix):
    luns = test_utils.get_luns(
        prefix, SD_ISCSI_HOST_NAME, SD_ISCSI_PORT, SD_ISCSI_TARGET, from_lun=SD_ISCSI_NR_LUNS+1)
    dlun_params = sdk4.types.Disk(
        name=DLUN_DISK_NAME,
        format=sdk4.types.DiskFormat.RAW,
        lun_storage=sdk4.types.HostStorage(
            type=sdk4.types.StorageType.ISCSI,
            logical_units=luns,
        ),
    )

    api = prefix.virt_env.engine_vm().get_api_v4()
    engine = api.system_service()
    disk_attachments_service = test_utils.get_disk_attachments_service(engine, VM0_NAME)
    with test_utils.TestEvent(engine, 97):
        disk_attachments_service.add(sdk4.types.DiskAttachment(
            disk=dlun_params,
            interface=sdk4.types.DiskInterface.VIRTIO_SCSI))

        disk_service = test_utils.get_disk_service(engine, DLUN_DISK_NAME)
        attachment_service = disk_attachments_service.attachment_service(disk_service.get().id)
        assert attachment_service.get() is not None, \
            'Failed to attach Direct LUN disk to {}'.format(VM0_NAME)
