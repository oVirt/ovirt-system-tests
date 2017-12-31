
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
import contextlib

from ovirtsdk4 import types

from lib import syncutil, clusterlib
from lib.sdkentity import SDKRootEntity


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


class Host(SDKRootEntity):

    @property
    def name(self):
        return self.sdk_type.name

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

    def clean_networks(self):
        mgmt_net_id = self._get_mgmt_net_attachment().network.id
        removed_attachments = [att for att in self._get_existing_attachments()
                               if att.network.id != mgmt_net_id]
        self.service.setup_networks(
            removed_network_attachments=removed_attachments
        )

    @contextlib.contextmanager
    def wait_for_up_status(self, timeout=5 * 60):
        yield
        syncutil.sync(exec_func=lambda: self._service.get().status,
                      exec_func_args=(),
                      success_criteria=self._host_up_status_success_criteria,
                      timeout=timeout)

    def _build_sdk_type(self, cluster, vm):
        return types.Host(
            name=vm.name(),
            description='host %s' % vm.name(),
            address=vm.name(),
            root_password=str(vm.root_password()),
            override_iptables=True,
            cluster=types.Cluster(name=cluster)
        )

    def _get_parent_service(self, system):
        return system.hosts_service

    def _host_up_status_success_criteria(self, host_status):
        if host_status == types.HostStatus.UP:
            return True
        if host_status in (types.HostStatus.NON_OPERATIONAL,
                           types.HostStatus.INSTALL_FAILED,
                           types.HostStatus.NON_RESPONSIVE):
            raise HostStatusError('{} is {}'.format(self.name, host_status))
        return False

    def _create_network_attachment(self, attachment_data):
        network = attachment_data.network
        ip_configuration = attachment_data.ip_configuration

        attachment = types.NetworkAttachment(
            network=network.sdk_type,
            host_nic=types.HostNic(name=attachment_data.nic_name)
        )
        if ip_configuration is not None:
            attachment.ip_address_assignments = ip_configuration
        return attachment

    def _removed_net_attachments(self, modified_networks):
        return [attachment for attachment in self._get_existing_attachments()
                if attachment.network.name not in modified_networks]

    def _get_mgmt_net_attachment(self):
        mgmt_network = self._cluster().mgmt_network()
        return next(att for att in self._get_existing_attachments()
                    if att.network.id == mgmt_network.id)

    def _get_existing_attachments(self):
        return list(self.service.network_attachments_service().list())

    def _cluster(self):
        cluster = clusterlib.Cluster(self._parent_sdk_system)
        cluster.import_by_id(self.sdk_type.cluster.id)
        return cluster
