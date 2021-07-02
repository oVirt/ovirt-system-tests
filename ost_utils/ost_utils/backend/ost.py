#
# Copyright 2020 Red Hat, Inc.
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

import json

from ost_utils.backend import base
from ost_utils import memoized
from ost_utils import shell


class OstBackend(base.BaseBackend):

    def __init__(self, prefix_path):
        self._prefix_path = prefix_path
        self._ansible_inventory_str = None

    def iface_mapping(self):
        status = self._status()

        mapping = {}

        for vm_name, vm_desc in status["VMs"].items():
            networks = mapping.setdefault(vm_name, {})
            for nic_name, nic_desc in vm_desc["NICs"].items():
                networks.setdefault(nic_desc, []).append(nic_name)

        return mapping

    def ansible_inventory_str(self):
        if self._ansible_inventory_str is None:
            contents = shell.shell(["cat", "hosts"],
                                   bytes_output=True,
                                   cwd=self._prefix_path)
            self._ansible_inventory_str = contents
        return self._ansible_inventory_str

    def artifacts(self):
        return {}

    def deploy_scripts(self):
        status = self._status()

        mapping = {}

        for vm_name, vm_desc in status["VMs"].items():
            deploy_scripts = mapping.setdefault(vm_name, [])
            for deploy_script in vm_desc["deploy-scripts"]:
                deploy_scripts.append(deploy_script)

        return mapping

    @memoized.memoized
    def _status(self):
        status = shell.shell(
            ["bash", "-c", "source lagofy.sh; ost_status"],
            cwd=self._prefix_path + '/..'
        )
        return json.loads(status)

    @memoized.memoized
    def libvirt_net_name(self, net_name):
        return self._status()["Networks"][net_name]
