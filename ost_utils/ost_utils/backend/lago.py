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

from __future__ import absolute_import

import json
import os

from ost_utils import memoized
from ost_utils import shell


@memoized.memoized
def _status():
    prefix_path = os.environ["PREFIX"]
    status = shell.shell(
        ["lago", "--out-format", "json", "status"], cwd=prefix_path
    )
    return json.loads(status)


def _find_network(part):
    return next(
        n
        for n in _status()["Prefix"]["Networks"]
        if n.find(part) > 0
    )


@memoized.memoized
def management_network_name():
    return _find_network("management")


@memoized.memoized
def storage_network_name():
    return _find_network("storage")


@memoized.memoized
def bonding_network_name():
    return _find_network("bonding")


@memoized.memoized
def iface_mapping():
    status = _status()
    vms = status["Prefix"]["VMs"]

    mapping = {}

    for vm_name, vm_desc in vms.items():
        networks = mapping.setdefault(vm_name, {})
        for nic_name, nic_desc in vm_desc["NICs"].items():
            networks.setdefault(nic_desc["network"], []).append(nic_name)

    return mapping
