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
import os
import tempfile
import threading

import yaml

from ost_utils.backend import base
from ost_utils import memoized
from ost_utils import shell


class LagoBackend(base.BaseBackend):

    def __init__(self, prefix_path):
        self._prefix_path = prefix_path
        self._ansible_inventory = None
        self._lock = threading.Lock()

    def iface_mapping(self):
        status = self._status()
        vms = status["Prefix"]["VMs"]

        mapping = {}

        for vm_name, vm_desc in vms.items():
            networks = mapping.setdefault(vm_name, {})
            for nic_name, nic_desc in vm_desc["NICs"].items():
                networks.setdefault(nic_desc["network"], []).append(nic_name)

        return mapping

    def ansible_inventory(self):
        with self._lock:
            if self._ansible_inventory is None:
                contents = shell.shell(["lago", "ansible_hosts"],
                                       bytes_output=True,
                                       cwd=self._prefix_path)
                inventory = tempfile.NamedTemporaryFile()
                inventory.write(contents)
                inventory.flush()
                os.fsync(inventory.fileno())
                self._ansible_inventory = inventory

        return self._ansible_inventory.name

    def artifacts(self):
        init_file = self._init_file()
        return {
            hostname: init_file['domains'][hostname]['artifacts']
            for hostname in self.hostnames()
        }

    def deploy_scripts(self):
        init_file = self._init_file()
        return {
            hostname:
                init_file['domains'][hostname].get(
                    'metadata', {}).get('deploy-scripts', [])
            for hostname in self.hostnames()
        }

    @memoized.memoized
    def _status(self):
        status = shell.shell(
            ["lago", "--out-format", "json", "status"], cwd=self._prefix_path
        )
        return json.loads(status)

    @memoized.memoized
    def _init_file(self):
        path = os.environ.get("LAGO_INIT_FILE", None)

        if path is None:
            raise RuntimeError("'LAGO_INIT_FILE' variable is not defined")

        with open(path, 'rb') as init_file:
            return yaml.safe_load(init_file.read())
