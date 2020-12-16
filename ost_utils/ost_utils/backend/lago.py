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


class LagoBackend(base.BaseBackend):

    def __init__(self, prefix_path):
        self._prefix_path = prefix_path

    def iface_mapping(self):
        status = self._status()
        vms = status["Prefix"]["VMs"]

        mapping = {}

        for vm_name, vm_desc in vms.items():
            networks = mapping.setdefault(vm_name, {})
            for nic_name, nic_desc in vm_desc["NICs"].items():
                networks.setdefault(nic_desc["network"], []).append(nic_name)

        return mapping

    @memoized.memoized
    def _status(self):
        status = shell.shell(
            ["lago", "--out-format", "json", "status"], cwd=self._prefix_path
        )
        return json.loads(status)
