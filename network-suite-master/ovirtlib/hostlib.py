#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import contextlib

from ovirtsdk4 import types

from . import clusterlib
from . import error
from . import eventlib
from . import joblib
from . import netattachlib
from . import netlib
from . import syncutil
from .netattachlib import BondingData
from .netattachlib import NetworkAttachmentData
from .sdkentity import SDKRootEntity
from .sdkentity import SDKSubEntity

HOST_TIMEOUT_SHORT = 5 * 60
HOST_TIMEOUT_LONG = 20 * 60
SETUP_NETWORKS_TIMEOUT = 3 * 60


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

    @root_password.setter
    def root_password(self, password):
        self._root_password = password

    @property
    def status(self):
        return self.get_sdk_type().status

    @property
    def is_up(self):
        return self.status == types.HostStatus.UP

    @property
    def is_in_maintenance(self):
        return self.status == types.HostStatus.MAINTENANCE

    @property
    def is_spm(self):
        return self.get_sdk_type().spm.status == types.SpmStatus.SPM

    @property
    def is_not_spm(self):
        return self.get_sdk_type().spm.status == types.SpmStatus.NONE

    @property
    def bonds(self):
        bonds = []
        for sdk_nic in self._service.nics_service().list():
            if sdk_nic.bonding:
                bond = Bond(self)
                bond.import_by_id(sdk_nic.id)
                bonds.append(bond)
        return bonds

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
            cluster=cluster.get_sdk_type(),
        )
        self._create_sdk_entity(sdk_type)
        self._root_password = root_password

    def update(self, **kwargs):
        return syncutil.sync(
            exec_func=super(Host, self).update,
            exec_func_args=kwargs,
            error_criteria=lambda e: error.is_not_ovirt_or_unlisted(
                e,
                ['Cannot edit Host. Related operation is currently in progress'],
            ),
            sdk_entity=self,
        )

    def force_select_spm(self):
        syncutil.sync(
            exec_func=self.service.force_select_spm,
            exec_func_args=(),
            success_criteria=lambda r: self.is_spm,
            error_criteria=lambda e: error.is_not_ovirt_or_unlisted(
                e,
                [
                    'Cannot force select SPM. The Storage Pool has running tasks',
                    'Cannot force select SPM. Unknown Data Center status',
                    'is already SPM or contending',
                ],
            ),
        )

    def hand_over_spm(self, candidate_spm):
        if self.is_spm and candidate_spm.is_up:
            candidate_spm.force_select_spm()
            joblib.AllJobs(self.system).wait_for_done()

    def activate(self):
        syncutil.sync(
            exec_func=self._service.activate,
            exec_func_args=(),
            success_criteria=lambda s: self.is_up,
            error_criteria=lambda e: error.is_not_ovirt_or_unlisted(
                e,
                [
                    'Related operation is currently in progress',
                    'Cannot activate Host. Host in Up status',
                ],
            ),
            delay_start=30,
            retry_interval=30,
            timeout=3 * 60,
            sdk_entity=self,
        )
        joblib.AllJobs(self.system).wait_for_done()

    def deactivate(self):
        syncutil.sync(
            exec_func=self._service.deactivate,
            exec_func_args=(),
            timeout=3 * 60,
            success_criteria=lambda s: self.is_in_maintenance,
            error_criteria=lambda e: error.is_not_ovirt_or_unlisted(
                e,
                [
                    'Host has asynchronous running tasks',
                    'Host is contending',
                    'Host is already in Maintenance mode',
                ],
            ),
            sdk_entity=self,
        )
        joblib.AllJobs(self.system).wait_for_done()

    @contextlib.contextmanager
    def toggle_cluster(self, target_cluster):
        eventlib.EngineEvents(self.system).add(f'OST - before toggle cluster: {self.name} is spm({self.is_spm})')
        current_cluster = self.get_cluster()
        try:
            self.change_cluster(target_cluster)
            yield
        finally:
            self.change_cluster(current_cluster)

    @error.report_status
    def change_cluster(self, cluster):
        spm_before_deactivate = self.is_spm
        self.deactivate()
        syncutil.sync(
            exec_func=self.update,
            exec_func_args={'cluster': cluster.get_sdk_type()},
            success_criteria=lambda sdk_type: (hasattr(sdk_type, 'cluster') and sdk_type.cluster.id == cluster.id),
            sdk_entity=self,
        )
        self.activate()
        if spm_before_deactivate:
            # Deactivation removed SPM status from this host and caused the DC
            # to become Non Responsive. This is an unstable state.
            # Wait for stabilization indicated by DC state UP when either:
            # - another host becomes SPM after deactivating this host
            # - this host becomes SPM after its reactivation
            self._get_data_center().wait_for_up_status()

    def get_cluster(self):
        cluster = clusterlib.Cluster(self.system)
        cluster.import_by_id(self.get_sdk_type().cluster.id)
        return cluster

    def setup_networks(
        self,
        attachments_data=(),
        remove_other_networks=True,
        sync_networks=False,
        bonding_data=(),
    ):
        """
        By default sets a desired network configuration state on the host
        which means that unspecified network attachments are removed.
        To prevent removal of unspecified attachments specify
        remove_other_networks=False.

        By default out-of-sync networks are not synced. This might fail the
        whole request because engine API forbids modifying an out-of-sync
        network. To enable syncing out-of-sync networks before modifying them
        specify sync_networks=True.

        :param attachments_data: []NetworkAttachmentData
        :param remove_other_networks: Boolean
        :param sync_networks: Boolean
        :param bonding_data: []BondingData
        """
        modified_net_attachments = [att_data.to_network_attachment() for att_data in attachments_data]

        removed_net_attachments = (
            self._get_complementary_net_attachments(
                self._get_net_ids_for_attachment_data(list(attachments_data) + [self.get_mgmt_net_attachment_data()])
            )
            if remove_other_networks
            else None
        )

        synced_net_attachments = modified_net_attachments if sync_networks else None

        modified_bonds = [bond_data.to_bond() for bond_data in bonding_data]

        return self.service.setup_networks(
            modified_bonds=modified_bonds,
            modified_network_attachments=modified_net_attachments,
            removed_network_attachments=removed_net_attachments,
            synchronized_network_attachments=synced_net_attachments,
            check_connectivity=True,
        )

    def remove_networks(self, removed_networks):
        removed_network_ids = netlib.Network.get_networks_ids(removed_networks)
        removed_attachments = self._get_existing_attachments_for_network_ids(removed_network_ids)
        return self._remove_setup_networks(removed_attachments)

    def remove_attachments(self, removed_attachments_data=(), removed_bonding_data=()):
        """
        :param removed_attachments_data: []netattachlib.NetworkAttachmentData
        :param removed_bonding_data: []netattachlib.BondingData
        """
        removed_bond_names = BondingData.get_bonds_names(removed_bonding_data)
        removed_bonds = self._get_nics_by_name(removed_bond_names)
        net_attachments = NetworkAttachmentData.to_network_attachments(removed_attachments_data)
        return self._remove_setup_networks(net_attachments, removed_bonds)

    def _remove_setup_networks(self, net_attachments, removed_bonds=None):
        """
        :param net_attachments: []types.NetworkAttachment
        :param removed_bonds: []types.HostNic
        """
        return self.service.setup_networks(
            removed_network_attachments=net_attachments,
            removed_bonds=removed_bonds,
            check_connectivity=True,
        )

    def networks_in_sync(self, networks=None):
        attachments = self._get_attachments_for_networks(networks)
        return all(att.in_sync for att in attachments)

    def networks_out_of_sync(self, networks=None):
        attachments = self._get_attachments_for_networks(networks)
        return all(not att.in_sync for att in attachments)

    def are_networks_attached(self, networks):
        attachments = self._get_attachments_for_networks(networks)
        return bool(attachments)

    def _get_attachments_for_networks(self, networks):
        if networks is None:
            attachments = self._get_existing_attachments()
        else:
            network_ids = {net.id for net in networks}
            attachments = [att for att in self._get_existing_attachments() if att.network.id in network_ids]
        return attachments

    def _get_existing_attachments_for_network_ids(self, network_ids):
        return [attachment for attachment in self._get_existing_attachments() if attachment.network.id in network_ids]

    def clean_all_networking(self):
        self.clean_networks()
        self.clean_bonds()

    def clean_networks(self):
        mgmt_net_id = self._get_mgmt_net_attachment().network.id
        removed_attachments = [att for att in self._get_existing_attachments() if att.network.id != mgmt_net_id]
        self.service.setup_networks(removed_network_attachments=removed_attachments)

    def clean_bonds(self):
        removed_bonds = [bond.get_sdk_type() for bond in self.bonds]
        self.service.setup_networks(removed_bonds=removed_bonds)

    def sync_all_networks(self):
        self.service.sync_all_networks()

    def copy_networks_from(self, source_host):
        self.service.copy_host_networks(source_host=source_host.get_sdk_type())

    def wait_for_up_status(self, timeout=HOST_TIMEOUT_SHORT):
        return syncutil.sync(
            exec_func=lambda: self.status,
            exec_func_args=(),
            success_criteria=self._host_up_status_success_criteria,
            timeout=timeout,
        )

    def wait_for_non_operational_status(self):
        NONOP = HostStatus.NON_OPERATIONAL
        syncutil.sync(
            exec_func=lambda: self.status,
            exec_func_args=(),
            success_criteria=lambda s: s == NONOP,
        )

    def wait_for_maintenance_status(self):
        syncutil.sync(
            exec_func=lambda: self.status,
            exec_func_args=(),
            success_criteria=lambda s: s == HostStatus.MAINTENANCE,
        )

    def wait_for_networks_in_sync(self, networks=None):
        syncutil.sync(
            exec_func=self.networks_in_sync,
            exec_func_args=(networks,),
            success_criteria=lambda s: s,
        )

    def wait_for_networks_out_of_sync(self, networks=None):
        syncutil.sync(
            exec_func=self.networks_out_of_sync,
            exec_func_args=(networks,),
            success_criteria=lambda s: s,
        )

    def wait_for_spm_status(self):
        syncutil.sync(
            exec_func=lambda: self.is_spm,
            exec_func_args=(),
            success_criteria=lambda spm: spm,
        )

    def workaround_bz_1779280(self):
        results = syncutil.re_run(
            exec_func=self.wait_for_up_status,
            exec_func_args=(),
            count=6,
            interval=10,
        )
        eventlib.EngineEvents(self.system).add(
            description=f'OST - retry wait for host up after install ' f'{self.name}: {[str(r) for r in results]}'
        )
        return results

    def _get_parent_service(self, system):
        return system.hosts_service

    def _host_up_status_success_criteria(self, host_status):
        if host_status == HostStatus.UP:
            return True
        if host_status in (
            HostStatus.NON_OPERATIONAL,
            HostStatus.INSTALL_FAILED,
        ):
            raise HostStatusError('{} is {}'.format(self.name, host_status))
        return False

    def _get_net_ids_for_attachment_data(self, attachments_data):
        return {att_data.network.id for att_data in attachments_data}

    def _get_complementary_net_attachments(self, network_ids):
        return [
            attachment for attachment in self._get_existing_attachments() if attachment.network.id not in network_ids
        ]

    def get_mgmt_net_attachment_data(self):
        return self.get_attachment_data_for_networks((self.get_mgmt_network(),))[0]

    def get_mgmt_network(self):
        mgmt_net_id = self._get_mgmt_cluster_network().id
        return self._get_network_by_id(mgmt_net_id)

    def get_attachment_data_for_networks(self, networks):
        network_attachments = self._get_attachments_for_networks(networks)
        network_attachments_data = []
        for attachment in network_attachments:
            datum = netattachlib.NetworkAttachmentData(
                self._get_network_by_id(attachment.network.id),
                self._get_nic_name(attachment.host_nic.id),
                id=attachment.id,
                in_sync=attachment.in_sync,
                nic_id=attachment.host_nic.id,
            )
            datum.set_ip_assignments(attachment)
            network_attachments_data.append(datum)
        return network_attachments_data

    def _get_nic_name(self, nic_id):
        return self.system.hosts_service.host_service(self.id).nics_service().nic_service(nic_id).get().name

    def _get_nics_by_name(self, nic_names):
        """
        :param nic_names: []str
        :return: []types.HostNic
        """
        return [host_nic for host_nic in self._service.nics_service().list() if host_nic.name in nic_names]

    def _get_network_by_id(self, network_id):
        dc = self._get_data_center()
        network = netlib.Network(dc)
        network.import_by_id(network_id)
        return network

    def _get_data_center(self):
        return self.get_cluster().get_data_center()

    def _get_mgmt_net_attachment(self):
        mgmt_cluster_network = self._get_mgmt_cluster_network()
        return next(att for att in self._get_existing_attachments() if att.network.id == mgmt_cluster_network.id)

    def _get_mgmt_cluster_network(self):
        return self.get_cluster().mgmt_network()

    def _get_existing_attachments(self):
        return list(self.service.network_attachments_service().list())

    def refresh_capabilities(self):
        self.service.refresh()

    def compare_nics_except_mgmt(self, other, comparator):
        self_nics = self._get_sorted_nics_without_mgmt()
        other_nics = other._get_sorted_nics_without_mgmt()
        return all(comparator(nic0, nic1) for (nic0, nic1) in zip(self_nics, other_nics))

    def _get_sorted_nics_without_mgmt(self):
        mgmt_net_id = self.get_mgmt_network().id
        nics = filter(lambda nic: nic.get_network_id() != mgmt_net_id, self.nics())
        return sorted(nics, key=lambda x: (x.name, x.get_network_id()))

    def get_nic_for_mac_address(self, mac_address):
        return next(filter(lambda nic: nic.mac_address == mac_address, self.nics()))

    def nics(self):
        nics = []
        for sdk_nic in self._service.nics_service().list():
            nic = HostNic(self)
            nic.import_by_id(sdk_nic.id)
            nics.append(nic)
        return nics

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'name:{self.name}, '
                f'address:{self.address}, '
                f'status:{self.status}, '
                f'is_spm:{self.is_spm}, '
                f'cluster:{self.get_cluster().name}, '
                f'id:{self.id}>'
            )
        )


@contextlib.contextmanager
def setup_networks(
    host,
    attach_data=(),
    remove_other_networks=True,
    sync_networks=False,
    bonding_data=(),
):
    host.setup_networks(
        attachments_data=attach_data,
        remove_other_networks=remove_other_networks,
        sync_networks=sync_networks,
        bonding_data=bonding_data,
    )
    try:
        yield
    finally:
        host.remove_attachments(attach_data, bonding_data)


class HostNic(SDKSubEntity):
    def create(self):
        pass

    def _get_parent_service(self, host):
        return host.service.nics_service()

    @property
    def name(self):
        return self.get_sdk_type().name

    @property
    def status(self):
        return self.get_sdk_type().status

    @property
    def mac_address(self):
        return self.get_sdk_type().mac.address

    @property
    def boot_protocol(self):
        return self.get_sdk_type().boot_protocol

    @property
    def ipv6_boot_protocol(self):
        return self.get_sdk_type().ipv6_boot_protocol

    @property
    def ip4_address(self):
        return self.get_sdk_type().ip.address

    @property
    def ip6_address(self):
        return self.get_sdk_type().ipv6.address

    def boot_protocol_equals(self, other):
        return self.boot_protocol == other.boot_protocol

    def ipv6_boot_protocol_equals(self, other):
        return self.ipv6_boot_protocol == other.ipv6_boot_protocol

    def is_static_ipv4(self):
        return self.boot_protocol == types.BootProtocol.STATIC

    def is_disabled_ipv4(self):
        return self.boot_protocol == types.BootProtocol.NONE

    def is_static_ipv6(self):
        return self.ipv6_boot_protocol == types.BootProtocol.STATIC

    def is_disabled_ipv6(self):
        return self.ipv6_boot_protocol == types.BootProtocol.NONE

    def is_same_network_attachment(self, other):
        return self.get_network_id() == other.get_network_id()

    def is_network_attached(self):
        return self.get_network_id() is not None

    def is_up(self):
        return self.status == types.NicStatus.UP

    def get_network_id(self):
        network = self.get_sdk_type().network
        return network.id if network else None

    def wait_for_up_status(self, timeout=HOST_TIMEOUT_SHORT):
        syncutil.sync(
            exec_func=self.is_up,
            exec_func_args=(),
            success_criteria=lambda s: s,
            timeout=timeout,
        )

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'name:{self.name}, '
                f'status:{self.status}, '
                f'ip4_addr:{self.ip4_address}, '
                f'ip6_addr:{self.ip6_address}, '
                f'boot_proto:{self.boot_protocol}, '
                f'ip6_boot_proto:{self.ipv6_boot_protocol}, '
                f'net_attached?{self.is_network_attached()}, '
                f'id:{self.id}>'
            )
        )


class Bond(HostNic):
    @property
    def active_slave(self):
        active_slave = self._updated_bonding().active_slave
        return self._to_nic(active_slave)

    @property
    def inactive_slaves(self):
        bonding = self._updated_bonding()
        inactive_slaves = [inactive for inactive in bonding.slaves if inactive.id != bonding.active_slave.id]
        return [self._to_nic(nic) for nic in inactive_slaves]

    @property
    def all_slaves(self):
        return self.inactive_slaves + [self.active_slave]

    @property
    def bonding_data(self):
        return netattachlib.BondingData(self.name, [nic.name for nic in self.all_slaves])

    def _to_nic(self, sdk_nic):
        nic = HostNic(self._parent_sdk_entity)
        nic.import_by_id(sdk_nic.id)
        return nic

    def _updated_bonding(self):
        return self.get_sdk_type().bonding

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'{super().__repr__()}, '
                f'slaves:{self.all_slaves}, '
                f'id:{self.id}>'
            )
        )
