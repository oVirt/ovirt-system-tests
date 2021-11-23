#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import ovirtsdk4
import ovirtsdk4.types as types

from ost_utils.memoized import memoized


@memoized
def get_nics_service(engine, vm_name):
    vm_service = get_vm_service(engine, vm_name)
    nics_service = vm_service.nics_service()
    return nics_service


def get_network_fiter_parameters_service(engine, vm_name):
    nics_service = get_nics_service(engine, vm_name)
    nic = nics_service.list()[0]
    return nics_service.nic_service(
        id=nic.id
    ).network_filter_parameters_service()


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
    template = templates_service.list(search=f'name={template_name}')[0]
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
    vm = next(
        (vm for vm in vms_service.list(query=query) if vm.name == vm_name),
        None,
    )
    if vm is None:
        return None
    else:
        return vms_service.vm_service(vm.id)


def get_storage_domain_disk_service_by_name(sd_service, disk_name):
    disks_service = sd_service.disks_service()
    # StorageDomainDisksService.list has no 'search' parameter and ignores
    # query={'name': 'spam'} so we have to do the filtering ourselves
    disk = next(
        (disk for disk in disks_service.list() if disk.name == disk_name), None
    )
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
    return next(
        (
            snap
            for snap in snapshots_service.list()
            if snap.description == description
        ),
        None,
    )


def quote_search_string(s):
    # TODO: this function should eventually be able to format strings in
    # a way that they will be properly passed on via the sdk to Engine.
    #
    # Escaped characters are currently broken, but strings containing spaces
    # are able to be passed with enclosing quotation marks.
    if '"' in s:
        raise ValueError(
            'Quotation marks currently can not be appear in search phrases'
        )
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
    except ovirtsdk4.Error:
        jobs = engine.jobs_service().list()
    return all(job.status != types.JobStatus.STARTED for job in jobs)


def get_first_active_host_by_name(engine):
    hosts = engine.hosts_service().list(search='status=up')
    return sorted(hosts, key=lambda host: host.name)[0]


def get_attached_storage_domain(data_center, name, service=False):
    storage_domains_service = data_center.storage_domains_service()
    # AttachedStorageDomainsService.list doesn't have the 'search' parameter
    # (StorageDomainsService.list does but this helper is overloaded)
    sd = next(sd for sd in storage_domains_service.list() if sd.name == name)
    return (
        storage_domains_service.storage_domain_service(sd.id)
        if service
        else sd
    )


def get_attached_storage_domain_disk_service(
    attached_storage, name, query=None
):
    disks_service = attached_storage.disks_service()
    disk = next(
        disk for disk in disks_service.list(query=query) if disk.name == name
    )
    return disks_service.disk_service(disk.id)
