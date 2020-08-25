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

import base64

from ovirtsdk4 import types


def get_uuids(ansible_vm):
    encoded = ansible_vm.slurp(src='/root/multipath.txt')['content']
    return [u.decode('utf-8') for u in base64.b64decode(encoded).splitlines()]


def create_lun_sdk_entries(uuids, ips, port, target):
    luns = []

    for uuid in uuids:
        for ip in ips:
            lun = types.LogicalUnit(
                id=uuid,
                address=ip,
                port=port,
                target=target,
                username='username',
                password='password',
            )
            luns.append(lun)

    return luns
