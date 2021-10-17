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

NICInfo = namedtuple(
    "NICInfo",
    "name libvirt_name mac network_info " "ip4_dhcp_entry ip6_dhcp_entry",
)

VMInfo = namedtuple("VMInfo", "name libvirt_name nics deploy_scripts")


class VirshBackend(base.BaseBackend):
    def __init__(self, deployment_path):
        self._deployment_path = deployment_path
        self._ansible_inventory_str = None

        self._networks = VirshNetworks(self._deployment_path)
        self._vms = self._get_vms(self._deployment_path)

    def iface_mapping(self):
        mapping = {}

        for vm_name, vm_info in self._vms.items():
            networks = mapping.setdefault(vm_name, {})
            for nic_name, nic_info in vm_info.nics.items():
                network_name = nic_info.network_info.ost_name
                networks.setdefault(network_name, []).append(nic_name)

        return mapping

    def ip_mapping(self):
        mapping = {}

        for vm_name, vm_info in self._vms.items():
            networks = mapping.setdefault(vm_name, {})
            for nic_name, nic_info in vm_info.nics.items():
                network_name = nic_info.network_info.ost_name
                ip_list = networks.setdefault(network_name, [])
                if nic_info.ip6_dhcp_entry is not None:
                    ip_list.append(nic_info.ip6_dhcp_entry.ip)
                if nic_info.ip4_dhcp_entry is not None:
                    ip_list.append(nic_info.ip4_dhcp_entry.ip)

        return mapping

    def ansible_inventory_str(self):
        if self._ansible_inventory_str is None:
            contents = shell(
                ["cat", "hosts"], bytes_output=True, cwd=self._deployment_path
            )
            self._ansible_inventory_str = contents
        return self._ansible_inventory_str

    def deploy_scripts(self):
        return {vm.name: vm.deploy_scripts for vm in self._vms.values()}

    def libvirt_net_name(self, ost_net_name):
        return self._networks.get_network_for_ost_name(
            ost_net_name
        ).libvirt_name

    def _get_nics(self, domain_xml):
        nics = {}
        for nic in domain_xml.findall("./devices/interface[@type='network']"):
            libvirt_name = nic.find("./alias[@name]").get("name")
            # FIXME: The logic below is wrong - there's nothing tying
            # up the libvirt alias with the nic name visible on the vm side.
            # It just so happens it works for our use cases. In the long term
            # we need to refactor backend interface not to rely on nic names.
            name = libvirt_name.replace("net", "eth")
            mac = nic.find("./mac[@address]").get("address")
            libvirt_network = nic.find("./source[@network]").get("network")
            network_info = self._networks.get_network_for_libvirt_name(
                libvirt_network
            )
            (
                ip4_dhcp_entry,
                ip6_dhcp_entry,
            ) = self._networks.find_host_dhcp_for_mac(mac)
            nics[name] = NICInfo(
                name,
                libvirt_name,
                mac,
                network_info,
                ip4_dhcp_entry,
                ip6_dhcp_entry,
            )

        return nics

    def _get_vms(self, deployment_path):
        vm_names = [
            name
            for name in shell("virsh list --name".split()).splitlines()
            if name[8:13] == "-ost-"
        ]

        vms = {}

        for libvirt_name in vm_names:
            xml_str = shell(f"virsh dumpxml {libvirt_name}".split()).strip()
            xml = ET.fromstring(xml_str)

            try:
                vm_working_dir = xml.find(
                    "./metadata/{OST:metadata}ost/ost-working-dir[@comment]"
                ).get("comment")
            except AttributeError:
                continue
            if vm_working_dir != deployment_path:
                continue

            name = libvirt_name[9:]
            deploy_scripts = [
                node.get("name")
                for node in xml.findall(
                    "./metadata/{OST:metadata}ost/ost-deploy-scripts/"
                    "script[@name]"
                )
            ]
            nics = self._get_nics(xml)
            vms[name] = VMInfo(name, libvirt_name, nics, deploy_scripts)

        return vms
