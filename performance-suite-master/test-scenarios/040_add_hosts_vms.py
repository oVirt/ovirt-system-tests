#
# Copyright 2017 Red Hat, Inc.
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
from nose import SkipTest
from ovirtsdk.xml import params

# TODO: import individual SDKv4 types directly (but don't forget sdk4.Error)
import ovirtsdk4 as sdk4
import ovirtsdk4.types as types

from lago import utils
from ovirtlago import testlib

import test_utils
from test_utils import network_utils_v4
from test_utils import constants
from test_utils import versioning

from ost_utils import general_utils

import logging
LOGGER = logging.getLogger(__name__)

API_V4 = True
MB = 2 ** 20

# DC/Cluster
DC_NAME = 'performance-dc'
DC_VER_MAJ, DC_VER_MIN = versioning.cluster_version()
SD_FORMAT = 'v4'
CLUSTER_NAME = 'performance-cluster'
DC_QUOTA_NAME = 'DC-QUOTA'

# Storage
MASTER_SD_TYPE = 'nfs'

# Simulate Hosts and Vms
USE_VDSMFAKE = os.environ.has_key('OST_USE_VDSMFAKE')
VMS_COUNT = int(os.environ.get('OST_VM_COUNT', 100))
HOST_COUNT = int(os.environ.get('OST_HOST_COUNT', 10))
VM_NAME = "vm"
VM_TEMPLATE = "template"
POOL_NAME = "pool"
TEMPLATE_BLANK = 'Blank'
VM1_NAME='vm1'
GLANCE_IMAGE_TO_IMPORT = 'CirrOS 0.4.0 for x86_64'

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
CIRROS_IMAGE_NAME = versioning.guest_os_image_name()
TEMPLATE_CIRROS = versioning.guest_os_template_name()


# Network
VM_NETWORK = 'VM_Network'
VM_NETWORK_VLAN_ID = 100
MIGRATION_NETWORK = 'Migration_Net'


@testlib.with_ovirt_prefix
def vdsmfake_setup(prefix):
    """
    Prepare a large setup using vdsmfake
    """

    playbookName = 'vdsmfake-setup.yml'
    engine = prefix.virt_env.engine_vm()
    playbook = os.path.join(os.environ.get('SUITE'),
                            'test-scenarios', playbookName)

    engine.copy_to(playbook, '/tmp/%s' % playbookName)

    result = engine.ssh(['ansible-playbook /tmp/%s' % playbookName])

    nt.eq_(
        result.code, 0, 'Setting up vdsmfake failed.'
                        ' Exit code is %s' % result.code
    )


# TODO: support resolving hosts over IPv6 and arbitrary network
def _get_host_ip(prefix, host_name):
    return prefix.virt_env.get_vm(host_name).ip()

def _get_host_all_ips(prefix, host_name):
    return prefix.virt_env.get_vm(host_name).all_ips()

def _hosts_in_dc(api, dc_name=DC_NAME):
    hosts = api.hosts.list(query='datacenter={} AND status=up'.format(dc_name))
    if hosts:
        return sorted(hosts, key=lambda host: host.name)
    raise RuntimeError('Could not find hosts that are up in DC %s' % dc_name)

def _hosts_in_dc_4(api, dc_name=DC_NAME, random_host=False):
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


def _host_status_to_print(hosts_service, hosts_list):
    dump_hosts = ''
    for host in hosts_list:
            host_service_info = hosts_service.host_service(host.id)
            dump_hosts += '%s: %s\n' % (host.name, host_service_info.get().status)
    return dump_hosts


def _wait_for_status(hosts_service, dc_name, status):
    up_status_seen = False
    for _ in general_utils.linear_retrier(attempts=120, iteration_sleeptime=1):
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


class FakeHostVm:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name

    def root_password(self):
        return 'password'


def get_fake_hosts():
    return [FakeHostVm('%s.vdsm.fake' % i) for i in range(1, HOST_COUNT)]

@testlib.with_ovirt_prefix
def add_hosts(prefix):
    hosts = get_fake_hosts() if USE_VDSMFAKE else prefix.virt_env.host_vms()
    if not USE_VDSMFAKE:
        for host in hosts:
            host.ssh(['chronyc', '-4', 'add', 'server', testlib.get_prefixed_name('engine')])
            host.ssh(['chronyc', '-4', 'makestep'])

    api = prefix.virt_env.engine_vm().get_api_v4()
    add_hosts_4(api, hosts)


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


@testlib.with_ovirt_prefix
def verify_add_hosts(prefix):
    hosts = prefix.virt_env.host_vms()

    api = prefix.virt_env.engine_vm().get_api_v4()
    verify_add_hosts_4(api)


def verify_add_hosts_4(api):
    hosts_service = api.system_service().hosts_service()
    total_hosts = hosts_service.list(search='datacenter={}'.format(DC_NAME))

    testlib.assert_true_within_long(
        lambda: _single_host_up(hosts_service, total_hosts)
    )

@testlib.with_ovirt_prefix
def verify_add_all_hosts(prefix):
    api = prefix.virt_env.engine_vm().get_api_v4()
    hosts_service = api.system_service().hosts_service()
    total_hosts = hosts_service.list(search='datacenter={}'.format(DC_NAME))

    testlib.assert_true_within_long(
        lambda: _all_hosts_up(hosts_service, total_hosts)
    )

    if not USE_VDSMFAKE:
        for host in prefix.virt_env.host_vms():
            host.ssh(['rm', '-rf', '/dev/shm/yum', '/dev/shm/*.rpm'])


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
    add_generic_nfs_storage_domain_4(prefix, SD_NFS_NAME, SD_NFS_HOST_NAME, SD_NFS_PATH, nfs_version='v4_2')


# TODO: add this over the storage network and with IPv6
def add_second_nfs_storage_domain(prefix):
    add_generic_nfs_storage_domain_4(prefix, SD_SECOND_NFS_NAME,
                                   SD_NFS_HOST_NAME, SD_SECOND_NFS_PATH)


def add_generic_nfs_storage_domain_4(prefix, sd_nfs_name, nfs_host_name, mount_path, sd_format=SD_FORMAT, sd_type='data', nfs_version='v4_1'):
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
    kwargs = {}
    if sd_format >= 'v4':
        if not versioning.cluster_version_ok(4, 1):
            kwargs['storage_format'] = sdk4.types.StorageFormat.V3
        elif not versioning.cluster_version_ok(4, 3):
            kwargs['storage_format'] = sdk4.types.StorageFormat.V4

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
        **kwargs
    )

    _add_storage_domain_4(api, p)


def add_iscsi_storage_domain(prefix):
    ret = prefix.virt_env.get_vm(SD_ISCSI_HOST_NAME).ssh(['cat', '/root/multipath.txt'])
    nt.assert_equals(ret.code, 0)
    lun_guids = ret.out.splitlines()[0:SD_ISCSI_NR_LUNS-1]

    add_iscsi_storage_domain_4(prefix, lun_guids)

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
    add_generic_nfs_storage_domain_4(prefix, SD_ISO_NAME, SD_ISO_HOST_NAME, SD_ISO_PATH, sd_format='v1', sd_type='iso', nfs_version='v3')


def add_templates_storage_domain(prefix):
    add_generic_nfs_storage_domain_4(prefix, SD_TEMPLATES_NAME, SD_TEMPLATES_HOST_NAME, SD_TEMPLATES_PATH, sd_format='v1', sd_type='export', nfs_version='v4_1')


@testlib.with_ovirt_api
def set_dc_quota_audit(api):
    dc = api.datacenters.get(name=DC_NAME)
    dc.set_quota_mode('audit')
    nt.assert_true(
        dc.update()
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
def add_blank_vms(api):
    engine = api.system_service()
    vms_service = engine.vms_service()

    vm_params = sdk4.types.Vm(
        os=sdk4.types.OperatingSystem(
            type='rhel_7x64',
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
    vm_params.memory = 256 * MB
    vm_params.memory_policy.guaranteed = 128 * MB
    vms_service.add(vm_params)
    backup_vm_service = test_utils.get_vm_service(engine, BACKUP_VM_NAME)

    vm_params.name = VM0_NAME
    least_hotplug_increment = 256 * MB
    required_memory = 384 * MB
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


@testlib.with_ovirt_api4
def add_nic(api):
    NIC_NAME = 'eth0'
    # Locate the vnic profiles service and use it to find the ovirmgmt
    # network's profile id:
    profiles_service = api.system_service().vnic_profiles_service()
    profile_id = next(
        (
            profile.id for profile in profiles_service.list()
            if profile.name == MANAGEMENT_NETWORK
        ),
        None
    )

    # Empty profile id would cause fail in later tests (e.g. add_filter):
    nt.assert_is_not_none(profile_id)

    # Locate the virtual machines service and use it to find the virtual
    # machine:
    vms_service = api.system_service().vms_service()
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


@testlib.with_ovirt_api4
def add_vm_template(api):
    sds = api.system_service().storage_domains_service()
    sd = sds.list(search='name=ovirt-image-repository')[0]
    sd_service = sds.storage_domain_service(sd.id)
    images_service = sd_service.images_service()
    images = images_service.list()

    image = next(
        (i for i in images if i.name == GLANCE_IMAGE_TO_IMPORT),
        None
    )

    # Find the service that manages the image that we found in the previous
    # step:
    image_service = images_service.image_service(image.id)

    # Import the image:
    image_service.import_(
        import_as_template=True,
        template=sdk4.types.Template(
            name=VM_TEMPLATE
        ),
        cluster=sdk4.types.Cluster(
            name=CLUSTER_NAME
        ),
        storage_domain=sdk4.types.StorageDomain(
            name=SD_NFS_NAME
        )
    )

    templates_service = api.system_service().templates_service()
    getTemplate = lambda: templates_service.list(search="name=%s" % VM_TEMPLATE)
    testlib.assert_true_within(
        lambda: len(getTemplate()) == 1 and
                sdk4.types.TemplateStatus.OK == getTemplate()[0].status,
        timeout=300
    )


@testlib.with_ovirt_api4
def add_vms(api):
    vm_pools_service = api.system_service().vm_pools_service()

    # Use the "add" method to create a new virtual machine pool:
    vm_pools_service.add(
        pool=sdk4.types.VmPool(
            name=POOL_NAME,
            cluster=sdk4.types.Cluster(
                name=CLUSTER_NAME,
            ),
            template=sdk4.types.Template(
                name=VM_TEMPLATE,
            ),
            size=VMS_COUNT,
            prestarted_vms=VMS_COUNT,
            max_user_vms=1,
        ),
    )

_TEST_LIST = [
    add_dc,
    add_cluster,
    add_hosts,
    verify_add_hosts,
    add_master_storage_domain,
    add_vm_template,
    verify_add_all_hosts,
    add_vms,
]


def test_gen():
    if USE_VDSMFAKE:
        _TEST_LIST.insert(0, vdsmfake_setup)
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
