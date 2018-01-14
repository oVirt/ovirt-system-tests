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

import collections
import functools

# Taken from https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
class memoized(object):
   '''Decorator. Caches a function's return value each time it is called.
   If called later with the same arguments, the cached value is returned
   (not reevaluated).
   '''
   def __init__(self, func):
      self.func = func
      self.cache = {}
   def __call__(self, *args):
      if not isinstance(args, collections.Hashable):
         # uncacheable. a list, for instance.
         # better to not cache than blow up.
         return self.func(*args)
      if args in self.cache:
         return self.cache[args]
      else:
         value = self.func(*args)
         self.cache[args] = value
         return value
   def __repr__(self):
      '''Return the function's docstring.'''
      return self.func.__doc__
   def __get__(self, obj, objtype):
      '''Support instance methods.'''
      return functools.partial(self.__call__, obj)


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
    vm = vms_service.list(search=vm_name)[0]
    if vm is None:
        return None
    return vms_service.vm_service(vm.id)


@memoized
def get_disk_service(engine, disk_name):
    disks_service = engine.disks_service()
    disk = disks_service.list(search=disk_name)[0]
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
    template = templates_service.list(search=template_name)[0]
    if template is None:
        return None
    return templates_service.template_service(template.id)


@memoized
def get_pool_service(engine, pool_name):
    vm_pools_service= engine.vm_pools_service()
    pool = vm_pools_service.list(search=pool_name)[0]
    return vm_pools_service.pool_service(pool.id)


@memoized
def get_storage_domain_service(engine, sd_name):
    storage_domains_service = engine.storage_domains_service()
    sd = storage_domains_service.list(search=sd_name)[0]
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
    cluster = clusters_service.list(search=cluster_name)[0]
    return clusters_service.cluster_service(cluster.id)


@memoized
def get_vm_snapshots_service(engine, vm_name):
    vm_service = get_vm_service(engine, vm_name)
    if vm_service is None:
        return None
    return vm_service.snapshots_service()


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
