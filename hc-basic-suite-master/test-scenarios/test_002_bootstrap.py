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
#
from __future__ import absolute_import

import functools
import os
import random
import ssl
import tempfile
import time

# TODO: import individual SDKv4 types directly (but don't forget sdk4.Error)
import ovirtsdk4 as sdk4
import ovirtsdk4.types as types
import pytest

from ost_utils import assertions
from ost_utils import backend
from ost_utils import engine_object_names
from ost_utils import engine_utils
from ost_utils import general_utils
from ost_utils.pytest import order_by
from ost_utils.pytest.fixtures import root_password
from ost_utils.pytest.fixtures.network import storage_network_name
from ost_utils.pytest.fixtures.virt import *
from ost_utils.selenium.grid.common import http_proxy_disabled
from ost_utils.storage_utils import domain
from ost_utils.storage_utils import glance
from ost_utils.storage_utils import lun
from ost_utils.storage_utils import nfs
from ost_utils import shell
from ost_utils import test_utils
from ost_utils import utils
from ost_utils import versioning

import logging
LOGGER = logging.getLogger(__name__)

MB = 2 ** 20
GB = 2 ** 30

# DC/Cluster
DC_VER_MAJ, DC_VER_MIN = versioning.cluster_version()
SD_FORMAT = 'v4'
DC_QUOTA_NAME = 'DC-QUOTA'
TEMPLATE_BLANK = 'Blank'

# Storage
# TODO temporarily use nfs instead of iscsi. Revert back once iscsi works in vdsm 4.4!
MASTER_SD_TYPE = 'nfs'

SD_NFS_NAME = 'nfs'
SD_SECOND_NFS_NAME = 'second-nfs'
SD_NFS_PATH = '/exports/nfs/share1'
SD_SECOND_NFS_PATH = '/exports/nfs/share2'

SD_ISCSI_NAME = 'iscsi'
SD_ISCSI_TARGET = 'iqn.2014-07.org.ovirt:storage'
SD_ISCSI_PORT = 3260
SD_ISCSI_NR_LUNS = 2
DLUN_DISK_NAME = 'DirectLunDisk'

SD_ISO_NAME = 'iso'
SD_ISO_PATH = '/exports/nfs/iso'

SD_TEMPLATES_NAME = 'templates'
SD_TEMPLATES_PATH = '/exports/nfs/exported'

SD_GLANCE_NAME = 'ovirt-image-repository'
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
    "test_he_deploy",
    "test_verify_engine_certs",
    "test_engine_health_status",
    "test_list_glance_images",
    "test_add_dc_quota",
    "test_add_quota_storage_limits",
    "test_add_quota_cluster_limits",
    "test_set_dc_quota_audit",
    "test_add_blank_vms",
    "test_add_nic",
]

def _hosts_in_dc(api, dc_name=engine_object_names.TEST_DC_NAME, random_host=False):
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

def _random_host_from_dc(api, dc_name=engine_object_names.TEST_DC_NAME):
    return _hosts_in_dc(api, dc_name, True)

def _random_host_service_from_dc(api, dc_name=engine_object_names.TEST_DC_NAME):
    host = _hosts_in_dc(api, dc_name, True)
    return api.system_service().hosts_service().host_service(id=host.id)

def _all_hosts_up(hosts_service, total_num_hosts, dc_name):
    installing_hosts = hosts_service.list(
        search='datacenter={} AND status=installing or status=initializing '
               'or status=connecting or status=reboot'.format(dc_name)
    )
    if len(installing_hosts) == total_num_hosts: # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(dc_name))
    if len(up_hosts) == total_num_hosts:
        return True

    # sometimes a second host is fast enough to go up without master SD, it then goes NonOperational with 5min autorecovery, let's poke it
    nonop_hosts = hosts_service.list(search='datacenter={} AND status=nonoperational'.format(dc_name))
    if len(nonop_hosts):
        for host in nonop_hosts:
            host_service = hosts_service.host_service(host.id)
            host_service.activate()
        return False

    _check_problematic_hosts(hosts_service, dc_name)

def _single_host_up(hosts_service, total_num_hosts, dc_name):
    installing_hosts = hosts_service.list(
        search='datacenter={} AND status=installing or status=initializing '
               'or status=connecting or status=reboot'.format(dc_name)
    )
    if len(installing_hosts) == total_num_hosts : # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(dc_name))
    if len(up_hosts):
        return True

    _check_problematic_hosts(hosts_service, dc_name)

def _check_problematic_hosts(hosts_service, dc_name):
    problematic_hosts = hosts_service.list(search='datacenter={} AND status != installing and status != initializing and status != reboot and status != non_responsive and status != up'.format(dc_name))
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
        LOGGER.debug(_host_status_to_print(hosts_service, all_hosts))
        # we use up_status_seen because we make sure the status is not flapping
        if up_hosts:
            if up_status_seen:
                break
            up_status_seen = True
        else:
            up_status_seen = False
    return all_hosts


@order_by(_TEST_LIST)
def test_he_deploy(suite_dir):
    shell.shell([suite_dir + '/he_deploy.sh'])


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
    #engine_fqdn = "ost-hc-basic-suite-master-engine"
    url = 'http://{}/ovirt-engine/services/pki-resource?resource=ca-certificate&format={}'

    with http_proxy_disabled(), tempfile.NamedTemporaryFile() as tmp:
        engine_download(url.format(engine_fqdn, key_format), tmp.name)
        try:
            verification_fn(tmp.name)
        except shell.ShellError:
            LOGGER.debug(
                "Certificate verification failed. Certificate contents:\n")
            LOGGER.debug(tmp.read())
            raise


@pytest.mark.parametrize("scheme", ["http", "https"])
@order_by(_TEST_LIST)
def test_engine_health_status(scheme, engine_fqdn, engine_download):
    url = '{}://{}/ovirt-engine/services/health'.format(scheme, engine_fqdn)

    with http_proxy_disabled():
        assert engine_download(url) == b"DB Up!Welcome to Health Status!"


@order_by(_TEST_LIST)
def test_add_dc_quota(engine_api, ost_dc_name):
    datacenters_service = engine_api.system_service().data_centers_service()
    datacenter = datacenters_service.list(search='name=%s' % ost_dc_name)[0]
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
        with engine_utils.wait_for_event(system_service, 998):
            all_images = glance_domain_service.images_service().list()
        if not len(all_images):
            raise RuntimeError('No GLANCE images available')
    except sdk4.Error:
        raise RuntimeError('GLANCE is not available: client request error')


@order_by(_TEST_LIST)
def test_set_dc_quota_audit(engine_api, ost_dc_name):
    dcs_service = engine_api.system_service().data_centers_service()
    dc = dcs_service.list(search='name=%s' % ost_dc_name)[0]
    dc_service = dcs_service.data_center_service(dc.id)
    assert dc_service.update(
        types.DataCenter(
            quota_mode=types.QuotaModeType.AUDIT,
        ),
    )


@order_by(_TEST_LIST)
def test_add_quota_storage_limits(engine_api, ost_dc_name):

    # Find the data center and the service that manages it:
    dcs_service = engine_api.system_service().data_centers_service()
    dc = dcs_service.list(search='name=%s' % ost_dc_name)[0]
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
def test_add_quota_cluster_limits(engine_api, ost_dc_name):
    datacenters_service = engine_api.system_service().data_centers_service()
    datacenter = datacenters_service.list(search='name=%s' % ost_dc_name)[0]
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
def test_add_blank_vms(engine_api, ost_cluster_name):
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
            name=ost_cluster_name,
        ),
        template=sdk4.types.Template(
            name=TEMPLATE_BLANK,
        ),
        display=sdk4.types.Display(
            smartcard_enabled=True,
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
        assertions.assert_true_within_short(
            lambda:
            vm_service.get().status == sdk4.types.VmStatus.DOWN
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
