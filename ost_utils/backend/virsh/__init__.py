#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import xml.etree.ElementTree as ET
from collections import namedtuple

from ost_utils.backend import base
from ost_utils.shell import shell

from ost_utils.backend.virsh.networking import VirshNetworks
from ost_utils.backend.virsh.networking import VMNics

VMInfo = namedtuple("VMInfo", "name libvirt_name nics deploy_scripts")


class VirshBackend(base.BaseBackend):
    def __init__(self, deployment_path):
        self._deployment_path = deployment_path
        self._ansible_inventory_str = None

        self._networks = VirshNetworks(self._deployment_path)
        self._vms = self._get_vms(self._deployment_path)

    def iface_mapping(self):
        return {vm_info.name: vm_info.nics.get_nics_for_all_networks() for vm_info in self._vms.values()}

    def ip_mapping(self):
        return {vm_info.name: vm_info.nics.ips_by_network_role() for vm_info in self._vms.values()}

    def mac_mapping(self):
        return {vm_info.name: vm_info.nics.macs_by_network_role() for vm_info in self._vms.values()}

    def ansible_inventory_str(self):
        if self._ansible_inventory_str is None:
            contents = shell(["cat", "hosts"], bytes_output=True, cwd=self._deployment_path)
            self._ansible_inventory_str = contents
        return self._ansible_inventory_str

    def deploy_scripts(self):
        return {vm.name: vm.deploy_scripts for vm in self._vms.values()}

    def libvirt_net_name(self, network_role):
        return self._networks.get_network_for_network_role(network_role).libvirt_name

    def management_subnet(self, ip_version):
        return self._networks.get_subnet_for_network_role(self.management_network_name(), ip_version)

    def bonding_subnet(self, ip_version):
        return self._networks.get_subnet_for_network_role(self.bonding_network_name(), ip_version)

    def storage_subnet(self, ip_version):
        return self._networks.get_subnet_for_network_role(self.storage_network_name(), ip_version)

    def _get_vms(self, deployment_path):
        vm_names = [name for name in shell("virsh list --name".split()).splitlines() if name[8:13] == "-ost-"]

        vms = {}

        for libvirt_name in vm_names:
            xml_str = shell(f"virsh dumpxml {libvirt_name}".split()).strip()
            xml = ET.fromstring(xml_str)

            try:
                vm_working_dir = xml.find("./metadata/{OST:metadata}ost/ost-working-dir[@comment]").get("comment")
            except AttributeError:
                continue
            if vm_working_dir != deployment_path:
                continue

            name = libvirt_name[9:]
            deploy_scripts = [
                node.get("name")
                for node in xml.findall("./metadata/{OST:metadata}ost/ost-deploy-scripts/" "script[@name]")
            ]
            nics = VMNics(xml, self._networks)
            vms[name] = VMInfo(name, libvirt_name, nics, deploy_scripts)

        return vms

    def get_ip_prefix_for_management_network(self, ip_version):
        management_role = self.management_network_name()
        mgmt_network = self._networks.get_network_for_network_role(management_role)
        if ip_version == 6:
            return mgmt_network.ip6_prefix
        return mgmt_network.ip4_prefix

    def get_gw_ip_for_management_network(self, ip_version):
        management_role = self.management_network_name()
        mgmt_network = self._networks.get_network_for_network_role(management_role)
        return mgmt_network.ip6_gw if ip_version == 6 else mgmt_network.ip4_gw
