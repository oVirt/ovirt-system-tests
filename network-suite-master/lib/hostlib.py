
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
import contextlib

import ovirtsdk4
from ovirtsdk4 import types

from lib import clusterlib
from lib import syncutil
from lib.sdkentity import SDKRootEntity


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


class NetworkAttachmentData(object):

    def __init__(self, network, nic_name, ip_configuration=None):
        self._network = network
        self._nic_name = nic_name
        self._ip_configuration = ip_configuration

    @property
    def network(self):
        return self._network

    @property
    def nic_name(self):
        return self._nic_name

    @property
    def ip_configuration(self):
        return self._ip_configuration


@contextlib.contextmanager
def change_cluster(host, cluster):
    original_cluster = host.get_cluster()

    host.change_cluster(cluster)
    try:
        yield
    finally:
        host.change_cluster(original_cluster)


class Host(SDKRootEntity):

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
        syncutil.sync(exec_func=self._deactivate,
                      timeout=3 * 60,
                      exec_func_args=(),
                      success_criteria=lambda s: s)

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
                       complement_management_network=True):
        """
        Sets a desired network configuration on the host, i.e. unspecified
        network attachments are removed.

        :param attachments_data: []NetworkAttachmentData
        :param complement_management_network: Boolean
        """

        modified_network_attachments = {
            att_data.network.name: self._create_network_attachment(att_data)
            for att_data in attachments_data
        }
        if complement_management_network:
            mgmt_attachment = self._get_mgmt_net_attachment()
            modified_network_attachments[mgmt_attachment.network.name] = \
                mgmt_attachment

        removed_network_attachments = self._removed_net_attachments(
            set(modified_network_attachments)
        )
        return self.service.setup_networks(
            modified_network_attachments=modified_network_attachments.values(),
            removed_network_attachments=removed_network_attachments,
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
        if networks is None:
            attachments = self._get_existing_attachments()
        else:
            network_ids = {net.id for net in networks}
            attachments = [att for att in self._get_existing_attachments()
                           if att.network.id in network_ids]
        return all(att.in_sync for att in attachments)

    def clean_networks(self):
        mgmt_net_id = self._get_mgmt_net_attachment().network.id
        removed_attachments = [att for att in self._get_existing_attachments()
                               if att.network.id != mgmt_net_id]
        self.service.setup_networks(
            removed_network_attachments=removed_attachments
        )

    def sync_all_networks(self):
        self.service.sync_all_networks()

    def wait_for_up_status(self, timeout=5 * 60):
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

    def _get_parent_service(self, system):
        return system.hosts_service

    def _host_up_status_success_criteria(self, host_status):
        if host_status == HostStatus.UP:
            return True
        if host_status in (HostStatus.NON_OPERATIONAL,
                           HostStatus.INSTALL_FAILED):
            raise HostStatusError('{} is {}'.format(self.name, host_status))
        return False

    def _create_network_attachment(self, attachment_data):
        network = attachment_data.network
        ip_configuration = attachment_data.ip_configuration

        attachment = types.NetworkAttachment(
            network=network.get_sdk_type(),
            host_nic=types.HostNic(name=attachment_data.nic_name)
        )
        if ip_configuration is not None:
            attachment.ip_address_assignments = ip_configuration
        return attachment

    def _removed_net_attachments(self, modified_networks):
        return [attachment for attachment in self._get_existing_attachments()
                if attachment.network.name not in modified_networks]

    def _get_mgmt_net_attachment(self):
        mgmt_network = self.get_cluster().mgmt_network()
        return next(att for att in self._get_existing_attachments()
                    if att.network.id == mgmt_network.id)

    def _get_existing_attachments(self):
        return list(self.service.network_attachments_service().list())

    def _deactivate(self):
        """Some host states are not represented by dedicated status (e.g.
        SPM contention). Although a status of a host may be 'Up', switching
        it to maintenance mode is not possible in some of these states.
        """

        HAS_RUNNING_TASKS = 'Host has asynchronous running tasks'
        HOST_IS_CONTENDING = 'Host is contending'

        try:
            self._service.deactivate()
            return True
        except ovirtsdk4.Error as e:
            msg = e.message
            if HAS_RUNNING_TASKS in msg or HOST_IS_CONTENDING in msg:
                return False
            raise


@contextlib.contextmanager
def setup_networks(host, attach_data):
    host.setup_networks(attach_data)
    try:
        yield
    finally:
        networks = [attach_datum.network for attach_datum in attach_data]
        host.remove_networks(networks)
