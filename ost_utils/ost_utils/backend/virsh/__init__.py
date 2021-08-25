#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import ipaddress
import xml.etree.ElementTree as ET

from collections import namedtuple

from ost_utils.backend import base
from ost_utils.shell import shell

DHCPEntry = namedtuple("DHCPEntry", "hostname mac_or_id ip")

NICInfo = namedtuple(
    "NICInfo",
    "name libvirt_name mac network_info " "ip4_dhcp_entry ip6_dhcp_entry",
)

NetworkInfo = namedtuple(
    "NetworkInfo",
    "name libvirt_name ip4_gw ip4_prefix ip4_dhcp_entries "
    "ip6_gw ip6_prefix ip6_dhcp_entries",
)

VMInfo = namedtuple("VMInfo", "name libvirt_name nics deploy_scripts")


class VirshBackend(base.BaseBackend):
    def __init__(self, deployment_path):
        self._deployment_path = deployment_path
        self._ansible_inventory_str = None

        self._networks = self._get_networks(self._deployment_path)
        networks = {n.libvirt_name: n for n in self._networks.values()}
        self._vms = self._get_vms(self._deployment_path, networks)

    def iface_mapping(self):
        mapping = {}

        for vm_name, vm_info in self._vms.items():
            networks = mapping.setdefault(vm_name, {})
            for nic_name, nic_info in vm_info.nics.items():
                network_name = nic_info.network_info.name
                networks.setdefault(network_name, []).append(nic_name)

        return mapping

    def ip_mapping(self):
        mapping = {}

        for vm_name, vm_info in self._vms.items():
            networks = mapping.setdefault(vm_name, {})
            for nic_name, nic_info in vm_info.nics.items():
                network_name = nic_info.network_info.name
                ip_list = networks.setdefault(network_name, [])
                if nic_info.ip6_dhcp_entry is not None:
                    ip_list.append(nic_info.ip6_dhcp_entry.ip)
                elif nic_info.ip4_dhcp_entry is not None:
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

    def libvirt_net_name(self, net_name):
        return self._networks[net_name].libvirt_name

    @staticmethod
    def _get_dhcp_entries(ip_node):
        dhcp_entries = {}

        for libvirt_dhcp_entry in ip_node.findall("./dhcp/host"):
            hostname = libvirt_dhcp_entry.get("name")
            mac_or_id = libvirt_dhcp_entry.get(
                "mac", libvirt_dhcp_entry.get("id")
            )
            ip = ipaddress.ip_address(libvirt_dhcp_entry.get("ip"))
            dhcp_entries[mac_or_id] = DHCPEntry(hostname, mac_or_id, ip)

        return dhcp_entries

    @staticmethod
    def _get_networks(deployment_path):
        libvirt_net_names = [
            name
            for name in shell("virsh net-list --name".split()).splitlines()
            if name.startswith("ost")
        ]

        networks = {}

        for name in libvirt_net_names:
            xml_str = shell(f"virsh net-dumpxml {name}".split()).strip()
            xml = ET.fromstring(xml_str)

            try:
                vm_working_dir = xml.find(
                    "./metadata/{OST:metadata}ost/ost-working-dir[@comment]"
                ).get("comment")
            except AttributeError:
                continue
            if vm_working_dir != deployment_path:
                continue

            ost_net_name = xml.find(
                "./metadata/{OST:metadata}ost/ost-network-type[@comment]"
            ).get("comment")

            ip4_gw = None
            ip4_prefix = None
            ip4_dhcp_entries = {}
            ip6_gw = None
            ip6_prefix = None
            ip6_dhcp_entries = {}

            for node in xml.findall("./ip"):
                if node.get("family", None) == "ipv6":
                    ip6_gw = ipaddress.ip_address(node.get("address"))
                    ip6_prefix = int(node.get("prefix"))
                    ip6_dhcp_entries = VirshBackend._get_dhcp_entries(node)
                else:
                    ip4_gw = ipaddress.ip_address(node.get("address"))
                    netmask = node.get("netmask")
                    ip4_prefix = ipaddress.IPv4Network(
                        f"0.0.0.0/{netmask}"
                    ).prefixlen
                    ip4_dhcp_entries = VirshBackend._get_dhcp_entries(node)

            networks[ost_net_name] = NetworkInfo(
                ost_net_name,
                name,
                ip4_gw,
                ip4_prefix,
                ip4_dhcp_entries,
                ip6_gw,
                ip6_prefix,
                ip6_dhcp_entries,
            )

        return networks

    @staticmethod
    def _find_dhcp_entries_for_nic(mac, networks):
        ip4_dhcp_entry = None
        ip6_dhcp_entry = None

        for network in networks.values():
            for dhcp_entry in network.ip4_dhcp_entries.values():
                if dhcp_entry.mac_or_id == mac:
                    ip4_dhcp_entry = dhcp_entry
                    break
            for dhcp_entry in network.ip6_dhcp_entries.values():
                if dhcp_entry.mac_or_id.endswith(mac):
                    ip6_dhcp_entry = dhcp_entry
                    break
            if ip4_dhcp_entry is not None and ip6_dhcp_entry is not None:
                break

        return (ip4_dhcp_entry, ip6_dhcp_entry)

    @staticmethod
    def _get_nics(domain_xml, networks):
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
            network_info = networks[libvirt_network]
            (
                ip4_dhcp_entry,
                ip6_dhcp_entry,
            ) = VirshBackend._find_dhcp_entries_for_nic(mac, networks)
            nics[name] = NICInfo(
                name,
                libvirt_name,
                mac,
                network_info,
                ip4_dhcp_entry,
                ip6_dhcp_entry,
            )

        return nics

    @staticmethod
    def _get_vms(deployment_path, networks):
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
            nics = VirshBackend._get_nics(xml, networks)
            vms[name] = VMInfo(name, libvirt_name, nics, deploy_scripts)

        return vms
