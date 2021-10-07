#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import base64

from ovirtsdk4 import types


def get_uuids(ansible_vm):
    encoded = ansible_vm.slurp(src='/root/multipath.txt')['content']
    return [u.decode('utf-8') for u in base64.b64decode(encoded).splitlines()]


def get_he_uuids(ansible_vm):
    encoded = ansible_vm.slurp(src='/root/he_multipath.txt')['content']
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
