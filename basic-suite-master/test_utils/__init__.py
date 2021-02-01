#
# Copyright 2017-2020 Red Hat, Inc.
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

import contextlib
import functools
import os
import ovirtsdk4.types as types
import random
import re
import six
import uuid
from ost_utils import assertions
from ost_utils.engine_utils import wait_for_event as TestEvent
from ost_utils.memoized import memoized
from test_utils.constants import VM0_IP_HOST_PART


if os.environ.get("USE_LAGO_OST_PLUGIN", "0") == "1":
    from ovirtlago import testlib  # pylint: disable=import-error

    def test_gen(tests, generator):
        '''Run the given tests amending their names according to the context.

        Tests suites are run repeatedly under different conditions, such as data
        center version as defined by OST_DC_VERSION environment variable.  This
        helper amends the run time test names to contain information about the
        environment under which they were run.

        Arguments:

          test_names -- sequence of names of the tests to run
          generator -- the calling test generator function providing test names to
            nose
        '''
        ost_dc_version = os.environ.get('OST_DC_VERSION', None)
        for t in testlib.test_sequence_gen(tests):
            test_id = t.description
            if ost_dc_version is not None:
                test_id = '{}_{}'.format(test_id, ost_dc_version.replace('.', ''))
            generator.__name__ = test_id
            yield t


@memoized
def get_nics_service(engine, vm_name):
    vm_service = get_vm_service(engine, vm_name)
    nics_service = vm_service.nics_service()
    return nics_service


def get_network_fiter_parameters_service(engine, vm_name):
    nics_service = get_nics_service(engine, vm_name)
    nic = nics_service.list()[0]
    return nics_service.nic_service(id=nic.id)\
        .network_filter_parameters_service()


@memoized
def get_vm_service(engine, vm_name):
    vms_service = engine.vms_service()
    vm = vms_service.list(search='name={}'.format(vm_name))[0]
    if vm is None:
        return None
    return vms_service.vm_service(vm.id)


@memoized
def get_disk_service(engine, disk_name):
    disks_service = engine.disks_service()
    disk = disks_service.list(search='name={}'.format(disk_name))[0]
    return disks_service.disk_service(disk.id)


@memoized
def get_disk_attachments_service(engine, vm_name):
    vm_service = get_vm_service(engine, vm_name)
    if vm_service is None:
        return None
    return vm_service.disk_attachments_service()


@memoized
def get_template_service(engine, template_name):
    templates_service = engine.templates_service()
    template = templates_service.list(search='name={}'.format(template_name))[0]
    if template is None:
        return None
    return templates_service.template_service(template.id)


@memoized
def get_pool_service(engine, pool_name):
    vm_pools_service = engine.vm_pools_service()
    pool = vm_pools_service.list(search='name={}'.format(pool_name))[0]
    return vm_pools_service.pool_service(pool.id)


@memoized
def get_storage_domain_service(engine, sd_name):
    storage_domains_service = engine.storage_domains_service()
    sd = storage_domains_service.list(search='name={}'.format(sd_name))[0]
    return storage_domains_service.storage_domain_service(sd.id)


def get_storage_domain_vm_service_by_name(sd_service, vm_name):
    vms_service = sd_service.vms_service()
    # StorageDomainVmsService.list has no 'search' parameter and ignores
    # query={'name': 'spam'} so we have to do the filtering ourselves
    vm = next((vm for vm in vms_service.list() if vm.name == vm_name), None)
    if vm is None:
        return None
    else:
        return vms_service.vm_service(vm.id)


def get_storage_domain_vm_service_by_query(sd_service, vm_name, query=None):
    vms_service = sd_service.vms_service()
    # StorageDomainVmsService.list has no 'search' parameter and ignores
    # query={'name': 'spam'} so we have to do the filtering ourselves
    vm = next((vm for vm in vms_service.list(query=query)
               if vm.name == vm_name), None)
    if vm is None:
        return None
    else:
        return vms_service.vm_service(vm.id)


def get_storage_domain_disk_service_by_name(sd_service, disk_name):
    disks_service = sd_service.disks_service()
    # StorageDomainDisksService.list has no 'search' parameter and ignores
    # query={'name': 'spam'} so we have to do the filtering ourselves
    disk = next((disk for disk in disks_service.list()
                 if disk.name == disk_name), None)
    if disk is None:
        return None
    else:
        return disks_service.disk_service(disk.id)


def hosts_in_cluster_v4(root, cluster_name):
    hosts = root.hosts_service().list(search='cluster={}'.format(cluster_name))
    return sorted(hosts, key=lambda host: host.name)


@memoized
def data_center_service(root, name):
    data_centers = root.data_centers_service()
    dc = data_centers.list(search='name={}'.format(name))[0]
    return data_centers.data_center_service(dc.id)


@memoized
def get_cluster_service(engine, cluster_name):
    clusters_service = engine.clusters_service()
    cluster = clusters_service.list(search='name={}'.format(cluster_name))[0]
    return clusters_service.cluster_service(cluster.id)


@memoized
def get_vm_snapshots_service(engine, vm_name):
    vm_service = get_vm_service(engine, vm_name)
    if vm_service is None:
        return None
    return vm_service.snapshots_service()


def get_snapshot(engine, vm_name, description):
    snapshots_service = get_vm_snapshots_service(engine, vm_name)
    return next((snap for snap in snapshots_service.list()
                 if snap.description == description),
                None)


def quote_search_string(s):
    # TODO: this function should eventually be able to format strings in
    # a way that they will be properly passed on via the sdk to Engine.
    #
    # Escaped characters are currently broken, but strings containing spaces
    # are able to be passed with enclosing quotation marks.
    if '"' in s:
        raise ValueError(
            'Quotation marks currently can not be appear in search phrases')
    return '"' + s + '"'


@memoized
def get_vnic_profiles_service(engine, network_name):
    networks_service = engine.networks_service()
    net = networks_service.list(search='name={}'.format(network_name))[0]
    return networks_service.network_service(net.id).vnic_profiles_service()


def all_jobs_finished(engine, correlation_id):
    try:
        jobs = engine.jobs_service().list(
            search='correlation_id=%s' % correlation_id
        )
    except:
        jobs = engine.jobs_service().list()
    return all(job.status != types.JobStatus.STARTED for job in jobs)


def assert_finished_within(
    func,
    engine,
    timeout,
    allowed_exceptions=None,
    *args,
    **kwargs
):

    if 'query' in kwargs:
        if 'correlation_id' not in kwargs['query']:
            kwargs['query']['correlation_id'] = uuid.uuid4()
    else:
        kwargs['query'] = {'correlation_id': uuid.uuid4()}

    func(*args, **kwargs)

    assertions.assert_true_within(
        lambda: all_jobs_finished(engine, kwargs['query']['correlation_id']),
        timeout
    )


assert_finished_within_long = functools.partial(
    assert_finished_within,
    timeout=assertions.LONG_TIMEOUT
)


def get_luns(prefix, host, port, target, from_lun, to_lun=None):
    out = prefix.virt_env.get_vm(host).ssh(['cat', '/root/multipath.txt']).out
    if six.PY3:
        out = out.decode('utf-8')
    if to_lun is not None: # take a range of LUNs
        lun_guids = out.splitlines()[from_lun:to_lun]
    else: # take a single LUN from the list.
        lun_guids = [out.splitlines()[from_lun]]
    if prefix.virt_env.get_net(testlib.get_prefixed_name('net-storage')): # use -net-storage network
       ips = prefix.virt_env.get_vm(host).ips_in_net(testlib.get_prefixed_name('net-storage'))
    else: # or get all IPs if suite doesn't have net-storage network
       ips = prefix.virt_env.get_vm(host).all_ips()
    luns = []
    for lun_id in lun_guids:
        for ip in ips:
            lun=types.LogicalUnit(
                id=lun_id,
                address=ip,
                port=port,
                target=target,
                username='username',
                password='password',
            )
            luns.append(lun)

    return luns


# unused in master, but sadly this is shared with he-basic-role-remote_suite_4.3, he-basic_suite_4.3, he-basic-iscsi_suite_4.3
def get_vm0_ip_address(prefix):
    gw_address = get_management_net(prefix).gw()
    return '.'.join(gw_address.split('.')[0:3] + [VM0_IP_HOST_PART])


def get_management_net(prefix):
    return prefix.virt_env.get_net()


def get_first_active_host_by_name(engine):
    hosts = engine.hosts_service().list(search='status=up')
    return sorted(hosts, key=lambda host: host.name)[0]


def get_attached_storage_domain(data_center, name, service=False):
    storage_domains_service = data_center.storage_domains_service()
    # AttachedStorageDomainsService.list doesn't have the 'search' parameter
    # (StorageDomainsService.list does but this helper is overloaded)
    sd = next(sd for sd in storage_domains_service.list() if sd.name == name)
    return storage_domains_service.storage_domain_service(
        sd.id) if service else sd


def get_attached_storage_domain_disk_service(attached_storage, name,
                                             query=None):
    disks_service = attached_storage.disks_service()
    disk = next(disk for disk in disks_service.list(query=query)
                if disk.name == name)
    return disks_service.disk_service(disk.id)
