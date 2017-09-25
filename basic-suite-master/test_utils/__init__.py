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
def get_nics_service(engine, vm_name):
    vm_service = get_vm_service(engine, vm_name)
    nics_service = vm_service.nics_service()
    return nics_service


def get_network_fiter_parameters_service(engine, vm_name):
    nics_service = get_nics_service(engine, vm_name)
    nic = nics_service.list()[0]
    return nics_service.nic_service(id=nic.id)\
        .network_filter_parameters_service()


def get_vm_service(engine, vm_name):
    vms_service = engine.vms_service()
    vm = vms_service.list(search=vm_name)[0]
    if vm is None:
        return None
    return vms_service.vm_service(vm.id)


def get_disk_service(engine, diskname):
    disks_service = engine.disks_service()
    disk = disks_service.list(search=diskname)[0]
    return disks_service.disk_service(disk.id)


def get_storage_domain_service(engine, sd_name):
    storage_domains_service = engine.storage_domains_service()
    sd = storage_domains_service.list(search=sd_name)[0]
    return storage_domains_service.storage_domain_service(sd.id)


def get_storage_domain_vm_service_by_name(sd_service, vm_name):
    vms_service = sd_service.vms_service()
    # StorageDomainVmsService.list has no 'search' parameter and ignores
    # query={'name': 'spam'} so we have to do the filtering ourselves
    vm = next(vm for vm in vms_service.list() if vm.name == vm_name)
    return vms_service.vm_service(vm.id)


def hosts_in_cluster_v4(root, cluster_name):
    hosts = root.hosts_service().list(search='cluster={}'.format(cluster_name))
    return sorted(hosts, key=lambda host: host.name)


def data_center_service(root, name):
    data_centers = root.data_centers_service()
    dc = data_centers.list(search='name={}'.format(name))[0]
    return data_centers.data_center_service(dc.id)


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
