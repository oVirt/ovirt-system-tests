# Copyright 2017-2018 Red Hat, Inc.
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
from ovirtsdk4 import Connection


class SDKSystemRoot(object):

    def __init__(self):
        self._system_service = None

    @property
    def disks_service(self):
        return self._system_service.disks_service()

    @property
    def data_centers_service(self):
        return self._system_service.data_centers_service()

    @property
    def storage_domains_service(self):
        return self._system_service.storage_domains_service()

    @property
    def templates_service(self):
        return self._system_service.templates_service()

    @property
    def clusters_service(self):
        return self._system_service.clusters_service()

    @property
    def openstack_image_providers_service(self):
        return self._system_service.openstack_image_providers_service()

    @property
    def vnic_profiles_service(self):
        return self._system_service.vnic_profiles_service()

    @property
    def network_filters_service(self):
        return self._system_service.network_filters_service()

    @property
    def hosts_service(self):
        return self._system_service.hosts_service()

    @property
    def vms_service(self):
        return self._system_service.vms_service()

    @property
    def mac_pools_service(self):
        return self._system_service.mac_pools_service()

    @property
    def events_service(self):
        return self._system_service.events_service()

    @property
    def openstack_network_providers_service(self):
        return self._system_service.openstack_network_providers_service()

    def connect(self, url, username, password, ca_file=None, insecure=True):
        conn = Connection(url=url, username=username,
                          password=password, insecure=insecure,
                          ca_file=ca_file)
        self._system_service = conn.system_service()

    def import_conn(self, conn):
        self._system_service = conn.system_service()
