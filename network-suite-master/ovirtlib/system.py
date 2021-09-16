#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
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

    @property
    def networks_service(self):
        return self._system_service.networks_service()

    @property
    def jobs_service(self):
        return self._system_service.jobs_service()

    @property
    def users_service(self):
        return self._system_service.users_service()

    def connect(self, url, username, password, ca_file=None, insecure=True):
        conn = Connection(
            url=url,
            username=username,
            password=password,
            insecure=insecure,
            ca_file=ca_file,
        )
        self._system_service = conn.system_service()

    def import_conn(self, conn):
        self._system_service = conn.system_service()
