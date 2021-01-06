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

# TODO: import individual SDKv4 types directly (but don't forget sdk4.Error)
import ovirtsdk4 as sdk4
import ovirtsdk4.types as types
import pytest

import test_utils
from test_utils import network_utils_v4
from test_utils import constants

from ost_utils import assertions
from ost_utils import engine_utils
from ost_utils import general_utils
from ost_utils.pytest import order_by
from ost_utils.pytest.fixtures import root_password
from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.sdk import system_service
from ost_utils.storage_utils import nfs

from ost_utils import shell
from ost_utils import versioning

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
USE_VDSMFAKE = 'OST_USE_VDSMFAKE' in os.environ
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
SD_NFS_PATH = '/exports/nfs/share1'
SD_SECOND_NFS_PATH = '/exports/nfs/share2'

SD_ISCSI_NAME = 'iscsi'
SD_ISCSI_TARGET = 'iqn.2014-07.org.ovirt:storage'
SD_ISCSI_PORT = 3260
SD_ISCSI_NR_LUNS = 2

SD_ISO_NAME = 'iso'
SD_ISO_PATH = '/exports/nfs/iso'

SD_TEMPLATES_NAME = 'templates'
SD_TEMPLATES_PATH = '/exports/nfs/exported'

SD_GLANCE_NAME = 'ovirt-image-repository'
GLANCE_AVAIL = False


_TEST_LIST = [
    "test_vdsmfake_setup",
    "test_copy_storage_script",
    "test_add_dc",
    "test_add_cluster",
    "test_sync_time",
    "test_add_hosts",
    "test_configure_storage",
    "test_verify_add_hosts",
    "test_add_nfs_master_storage_domain",
    "test_add_vm_template",
    "test_verify_add_all_hosts",
    "test_add_vms",
]


@order_by(_TEST_LIST)
@pytest.mark.skipif(USE_VDSMFAKE == False, reason="VDSMFAKE test")
def test_vdsmfake_setup(ansible_engine):
    """
    Prepare a large setup using vdsmfake
    """

    playbook_name = 'vdsmfake-setup.yml'
    playbook = os.path.join(os.environ.get('SUITE'),
                            'test-scenarios', playbook_name)

    ansible_engine.copy(
        src=playbook,
        dest=f"/tmp/{playbook_name}"
    )

    ansible_engine.shell('ansible-playbook /tmp/%s' % playbook_name)


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
    return _hosts_in_dc(api, dc_name, True)

def _all_hosts_up(hosts_service, total_num_hosts):
    installing_hosts = hosts_service.list(search='datacenter={} AND status=installing or status=initializing or status=connecting'.format(DC_NAME))
    if len(installing_hosts) == total_num_hosts: # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(DC_NAME))
    if len(up_hosts) == total_num_hosts:
        return True

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


@order_by(_TEST_LIST)
def test_add_dc(system_service):
    dcs_service = system_service.data_centers_service()
    with engine_utils.wait_for_event(system_service, 950): # USER_ADD_STORAGE_POOL
        assert dcs_service.add(
            sdk4.types.DataCenter(
                name=DC_NAME,
                description='APIv4 DC',
                local=False,
                version=sdk4.types.Version(major=DC_VER_MAJ,minor=DC_VER_MIN),
            ),
        )


@order_by(_TEST_LIST)
def test_add_cluster(system_service):
    clusters_service = system_service.clusters_service()
    assert clusters_service.add(
        sdk4.types.Cluster(
            name=CLUSTER_NAME,
            description='APIv4 Cluster',
            data_center=sdk4.types.DataCenter(
                name=DC_NAME,
            ),
            ballooning_enabled=True,
        ),
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


@order_by(_TEST_LIST)
@pytest.mark.skipif(USE_VDSMFAKE == True, reason='Using vdsmfake')
def test_sync_time(ansible_hosts, engine_hostname):
    ansible_hosts.shell('chronyc -4 add server {}'.format(engine_hostname))
    ansible_hosts.shell('chronyc -4 makestep')


@order_by(_TEST_LIST)
def test_add_hosts(ansible_host0_facts, ansible_host1_facts, system_service,
                   root_password):

    if USE_VDSMFAKE:
        hostnames = get_fake_hosts()
    else:
        hostnames = [
            facts.get("ansible_hostname")
            for facts in [ansible_host0_facts, ansible_host1_facts]
        ]

    def _add_host(hostname):
        return system_service.hosts_service().add(
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

    with engine_utils.wait_for_event(system_service, 42): # USER_ADD_VDS
        for hostname in hostnames:
            assert _add_host(hostname)


@order_by(_TEST_LIST)
def test_verify_add_hosts(system_service):
    hosts_service = system_service.hosts_service()
    hosts_status = hosts_service.list(search='datacenter={}'.format(DC_NAME))
    total_hosts = len(hosts_status)
    dump_hosts = _host_status_to_print(hosts_service, hosts_status)
    LOGGER.debug('Host status, verify_add_hosts:\n {}'.format(dump_hosts))
    assertions.assert_true_within(
        lambda: _single_host_up(hosts_service, total_hosts),
        timeout=constants.ADD_HOST_TIMEOUT
    )


@order_by(_TEST_LIST)
def test_verify_add_all_hosts(system_service):
    hosts_service = system_service.hosts_service()
    total_hosts = len(hosts_service.list(search='datacenter={}'.format(DC_NAME)))

    assertions.assert_true_within(
        lambda: _all_hosts_up(hosts_service, total_hosts),
        timeout=constants.ADD_HOST_TIMEOUT
    )


def _add_storage_domain_4(api, p):
    system_service = api.system_service()
    sds_service = system_service.storage_domains_service()
    sd = sds_service.add(p)

    sd_service = sds_service.storage_domain_service(sd.id)
    assertions.assert_true_within_long(
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
    assertions.assert_true_within_long(
        lambda: attached_sd_service.get().status == sdk4.types.StorageDomainStatus.ACTIVE
    )


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


@order_by(_TEST_LIST)
def test_add_vm_template(system_service):
    sds = system_service.storage_domains_service()
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

    templates_service = system_service.templates_service()

    def template_available(templates_service):
        get_template = templates_service.list(search="name=%s" % VM_TEMPLATE)
        if len(get_template) == 1 and \
               sdk4.types.TemplateStatus.OK == get_template[0].status:
            return True
        return False

    assertions.assert_true_within(
        lambda: template_available(templates_service),
        timeout=300
    )



@order_by(_TEST_LIST)
def test_add_vms(system_service):
    vm_pools_service = system_service.vm_pools_service()

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


@order_by(_TEST_LIST)
def test_copy_storage_script(ansible_engine):
    storage_script = os.path.join(
        os.environ.get('SUITE'),
        'deploy-scripts',
        'setup_storage.sh',
    )
    ansible_engine.copy(
        src=storage_script,
        dest='/tmp/setup_storage.sh',
        mode='0755'
    )


@order_by(_TEST_LIST)
def test_configure_storage(ansible_engine):
    ansible_engine.shell('/tmp/setup_storage.sh')
