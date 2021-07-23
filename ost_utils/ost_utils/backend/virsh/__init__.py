#
# Copyright 2021 Red Hat, Inc.
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

import ipaddress
import os
import xml.etree.ElementTree as ET

from collections import namedtuple

from ost_utils.backend import base
from ost_utils.shell import shell


NICInfo = namedtuple("NICInfo", "name libvirt_name mac network_info")

NetworkInfo = namedtuple(
    "NetworkInfo", "name libvirt_name ip4_gw ip4_prefix ip6_gw ip6_prefix"
)

VMInfo = namedtuple("VMInfo", "name libvirt_name nics deploy_scripts")


class VirshBackend(base.BaseBackend):
    def __init__(self, prefix_path):
        self._prefix_path = prefix_path
        self._ansible_inventory_str = None

        with open(os.path.join(self._prefix_path, "uuid")) as uuid_file:
            self._uuid = uuid_file.read().strip()

        self._networks = self._get_networks(self._uuid)
        networks = {n.libvirt_name: n for n in self._networks.values()}
        self._vms = self._get_vms(self._uuid, networks)

    def iface_mapping(self):
        mapping = {}

        for vm_name, vm_info in self._vms.items():
            networks = mapping.setdefault(vm_name, {})
            for nic_name, nic_info in vm_info.nics.items():
                network_name = nic_info.network_info.name
                networks.setdefault(network_name, []).append(nic_name)

        return mapping

    def ansible_inventory_str(self):
        if self._ansible_inventory_str is None:
            contents = shell(
                ["cat", "hosts"], bytes_output=True, cwd=self._prefix_path
            )
            self._ansible_inventory_str = contents
        return self._ansible_inventory_str

    def deploy_scripts(self):
        return {vm.name: vm.deploy_scripts for vm in self._vms.values()}

    def libvirt_net_name(self, net_name):
        return self._networks[net_name].libvirt_name

    @staticmethod
    def _get_networks(uuid):
        libvirt_net_names = [
            name
            for name in shell("virsh net-list --name".split()).splitlines()
            if uuid in name
        ]

        networks = {}

        for name in libvirt_net_names:
            xml_str = shell(f"virsh net-dumpxml {name}".split()).strip()
            xml = ET.fromstring(xml_str)

            ost_net_name = xml.find("./metadata[@comment]").get("comment")

            ip4_gw = None
            ip4_prefix = None
            ip6_gw = None
            ip6_prefix = None

            for node in xml.findall("./ip"):
                if node.get("family", None) == "ipv6":
                    ip6_gw = ipaddress.ip_address(node.get("address"))
                    ip6_prefix = int(node.get("prefix"))
                else:
                    ip4_gw = ipaddress.ip_address(node.get("address"))
                    netmask = node.get("netmask")
                    ip4_prefix = ipaddress.IPv4Network(
                        f"0.0.0.0/{netmask}"
                    ).prefixlen

            networks[ost_net_name] = NetworkInfo(
                ost_net_name, name, ip4_gw, ip4_prefix, ip6_gw, ip6_prefix
            )

        return networks

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
            nics[name] = NICInfo(name, libvirt_name, mac, network_info)

        return nics

    @staticmethod
    def _get_vms(uuid, networks):
        vm_names = [
            name
            for name in shell("virsh list --name".split()).splitlines()
            if uuid in name
        ]

        vms = {}

        for libvirt_name in vm_names:
            xml_str = shell(f"virsh dumpxml {libvirt_name}".split()).strip()
            xml = ET.fromstring(xml_str)
            name = libvirt_name.replace(f"{uuid}-", "", 1)
            deploy_scripts = [
                node.get("name")
                for node in xml.findall(
                    "./metadata/{OST metadata}ost/ost-deploy-scripts/"
                    "script[@name]"
                )
            ]
            nics = VirshBackend._get_nics(xml, networks)
            vms[name] = VMInfo(name, libvirt_name, nics, deploy_scripts)

        return vms
