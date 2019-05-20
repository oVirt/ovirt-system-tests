
# Copyright 2017-2019 Red Hat, Inc.
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
import contextlib

import ovirtsdk4
from ovirtsdk4 import types

from ovirtlib import clusterlib
from ovirtlib import netattachlib
from ovirtlib import netlib
from ovirtlib import syncutil
from ovirtlib.sdkentity import SDKRootEntity

HOST_TIMEOUT_SHORT = 5 * 60
HOST_TIMEOUT_LONG = 15 * 60


class HostStatus(object):

    CONNECTING = types.HostStatus.CONNECTING
    DOWN = types.HostStatus.DOWN
    ERROR = types.HostStatus.ERROR
    INITIALIZING = types.HostStatus.INITIALIZING
    INSTALL_FAILED = types.HostStatus.INSTALL_FAILED
    INSTALLING = types.HostStatus.INSTALLING
    INSTALLING_OS = types.HostStatus.INSTALLING_OS
    KDUMPING = types.HostStatus.KDUMPING
    MAINTENANCE = types.HostStatus.MAINTENANCE
    NON_OPERATIONAL = types.HostStatus.NON_OPERATIONAL
    NON_RESPONSIVE = types.HostStatus.NON_RESPONSIVE
    PENDING_APPROVAL = types.HostStatus.PENDING_APPROVAL
    PREPARING_FOR_MAINTENANCE = types.HostStatus.PREPARING_FOR_MAINTENANCE
    REBOOT = types.HostStatus.REBOOT
    UNASSIGNED = types.HostStatus.UNASSIGNED
    UP = types.HostStatus.UP


class HostStatusError(Exception):
    pass


@contextlib.contextmanager
def change_cluster(host, cluster):
    original_cluster = host.get_cluster()

    host.change_cluster(cluster)
    try:
        yield
    finally:
        host.change_cluster(original_cluster)


class Host(SDKRootEntity):

    def __init__(self, parent_sdk_system):
        super(Host, self).__init__(parent_sdk_system)
        self._root_password = None

    @property
    def name(self):
        return self.get_sdk_type().name

    @property
    def address(self):
        return self.get_sdk_type().address

    @property
    def root_password(self):
        return self._root_password

    @property
    def is_not_spm(self):
        return self.get_sdk_type().spm.status == types.SpmStatus.NONE

    def create(self, cluster, name, address, root_password):
        """
        :param cluster: clusterlib.Cluster
        :param name: str
        :param address: str
        :param root_password: str
        """
        sdk_type = types.Host(
            name=name,
            description='host %s' % name,
            address=address,
            root_password=root_password,
            override_iptables=True,
            cluster=cluster.get_sdk_type()
        )
        self._create_sdk_entity(sdk_type)
        self._root_password = root_password

    def activate(self):
        self._service.activate()

    def deactivate(self):
        self.wait_for_up_status()
        syncutil.sync(
            exec_func=self._service.deactivate,
            exec_func_args=(),
            timeout=3 * 60,
            error_criteria=Host._is_error_non_transient
        )
        self.wait_for_maintenance_status()

    def change_cluster(self, cluster):
        self.deactivate()
        self.wait_for_maintenance_status()
        self.update(cluster=cluster.get_sdk_type())
        self.activate()
        self.wait_for_up_status()

    def get_cluster(self):
        cluster = clusterlib.Cluster(self._parent_sdk_system)
        cluster.import_by_id(self.get_sdk_type().cluster.id)
        return cluster

    def setup_networks(self, attachments_data,
                       remove_other_networks=True,
                       sync_networks=False):
        """
        By default sets a desired network configuration state on the host
        which means that unspecified network attachments are removed.
        To prevent removal of unspecified attachments specify
        remove_other_networks=True.

        By default out-of-sync networks are not synced. This might fail the
        whole request because engine API forbids modifying an out-of-sync
        network. To enable syncing out-of-sync networks before modifying them
        specify sync_networks=True.

        :param attachments_data: []NetworkAttachmentData
        :param remove_other_networks: Boolean
        :param sync_networks: Boolean
        """

        modified_network_attachments = {
            att_data.network.name: att_data.to_network_attachment()
            for att_data in attachments_data
        }
        removed_network_attachments = None
        if remove_other_networks:
            mgmt_attachment = self._get_mgmt_net_attachment()
            modified_network_attachments[mgmt_attachment.network.name] = \
                mgmt_attachment
            removed_network_attachments = self._removed_net_attachments(
                set(modified_network_attachments)
            )
        synced_net_attachment_values = None
        if sync_networks:
            synced_net_attachment_values = (
                modified_network_attachments.values()
            )
        return self.service.setup_networks(
            modified_network_attachments=modified_network_attachments.values(),
            removed_network_attachments=removed_network_attachments,
            synchronized_network_attachments=synced_net_attachment_values,
            check_connectivity=True
        )

    def remove_networks(self, removed_networks):
        removed_network_ids = [
            removed_network.id for removed_network in removed_networks
        ]

        removed_attachments = [
            attachment for attachment in self._get_existing_attachments()
            if attachment.network.id in removed_network_ids
        ]

        return self.service.setup_networks(
            removed_network_attachments=removed_attachments,
            check_connectivity=True
        )

    def networks_in_sync(self, networks=None):
        attachments = self._get_attachments_for_networks(networks)
        return all(att.in_sync for att in attachments)

    def networks_out_of_sync(self, networks=None):
        attachments = self._get_attachments_for_networks(networks)
        return all(not att.in_sync for att in attachments)

    def _get_attachments_for_networks(self, networks):
        if networks is None:
            attachments = self._get_existing_attachments()
        else:
            network_ids = {net.id for net in networks}
            attachments = [att for att in self._get_existing_attachments()
                           if att.network.id in network_ids]
        return attachments

    def clean_networks(self):
        mgmt_net_id = self._get_mgmt_net_attachment().network.id
        removed_attachments = [att for att in self._get_existing_attachments()
                               if att.network.id != mgmt_net_id]
        self.service.setup_networks(
            removed_network_attachments=removed_attachments
        )

    def sync_all_networks(self):
        self.service.sync_all_networks()

    def wait_for_up_status(self, timeout=HOST_TIMEOUT_SHORT):
        syncutil.sync(exec_func=lambda: self.get_sdk_type().status,
                      exec_func_args=(),
                      success_criteria=self._host_up_status_success_criteria,
                      timeout=timeout)

    def wait_for_non_operational_status(self):
        NONOP = HostStatus.NON_OPERATIONAL
        syncutil.sync(exec_func=lambda: self.get_sdk_type().status,
                      exec_func_args=(),
                      success_criteria=lambda s: s == NONOP)

    def wait_for_maintenance_status(self):
        syncutil.sync(exec_func=lambda: self.get_sdk_type().status,
                      exec_func_args=(),
                      success_criteria=lambda s: s == HostStatus.MAINTENANCE)

    def wait_for_networks_in_sync(self, networks=None):
        syncutil.sync(exec_func=self.networks_in_sync,
                      exec_func_args=(networks,),
                      success_criteria=lambda s: s)

    def wait_for_networks_out_of_sync(self, networks=None):
        syncutil.sync(exec_func=self.networks_out_of_sync,
                      exec_func_args=(networks,),
                      success_criteria=lambda s: s)

    def _get_parent_service(self, system):
        return system.hosts_service

    def _host_up_status_success_criteria(self, host_status):
        if host_status == HostStatus.UP:
            return True
        if host_status in (HostStatus.NON_OPERATIONAL,
                           HostStatus.INSTALL_FAILED):
            raise HostStatusError('{} is {}'.format(self.name, host_status))
        return False

    def _removed_net_attachments(self, modified_networks):
        return [attachment for attachment in self._get_existing_attachments()
                if attachment.network.name not in modified_networks]

    def get_mgmt_net_attachment_data(self):
        return self._get_attachment_data_for_networks(
            (self.get_mgmt_network(),))[0]

    def get_mgmt_network(self):
        mgmt_net_id = self._get_mgmt_cluster_network().id
        return self._get_network_by_id(mgmt_net_id)

    def _get_attachment_data_for_networks(self, networks):
        network_attachments = self._get_attachments_for_networks(networks)
        network_attachments_data = []
        for attachment in network_attachments:
            datum = netattachlib.NetworkAttachmentData(
                self._get_network_by_id(attachment.network.id),
                self._get_nic_name(attachment.host_nic.id),
                id=attachment.id,
                in_sync=attachment.in_sync
            )
            datum.set_ip_assignments(attachment)
            network_attachments_data.append(datum)
        return network_attachments_data

    def _get_nic_name(self, nic_id):
        return (self._parent_sdk_system.hosts_service.host_service(self.id)
                .nics_service().nic_service(nic_id).get().name)

    def _get_network_by_id(self, network_id):
        dc = self._get_data_center()
        network = netlib.Network(dc)
        network.import_by_id(network_id)
        return network

    def _get_data_center(self):
        return self.get_cluster().get_data_center()

    def _get_mgmt_net_attachment(self):
        mgmt_cluster_network = self._get_mgmt_cluster_network()
        return next(att for att in self._get_existing_attachments()
                    if att.network.id == mgmt_cluster_network.id)

    def _get_mgmt_cluster_network(self):
        return self.get_cluster().mgmt_network()

    def _get_existing_attachments(self):
        return list(self.service.network_attachments_service().list())

    @staticmethod
    def _is_error_non_transient(error):
        HAS_RUNNING_TASKS = 'Host has asynchronous running tasks'
        HOST_IS_CONTENDING = 'Host is contending'

        if not isinstance(error, ovirtsdk4.Error):
            return True
        msg = error.args[0]
        if HAS_RUNNING_TASKS in msg or HOST_IS_CONTENDING in msg:
            return False
        return True

    def refresh_capabilities(self):
        self.service.refresh()


@contextlib.contextmanager
def setup_networks(host, attach_data, remove_other_networks=True,
                   sync_networks=False):
    host.setup_networks(
        attachments_data=attach_data,
        remove_other_networks=remove_other_networks,
        sync_networks=sync_networks
    )
    try:
        yield
    finally:
        networks = [attach_datum.network for attach_datum in attach_data]
        host.remove_networks(networks)
