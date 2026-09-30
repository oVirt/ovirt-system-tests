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


def create_lun_sdk_entries(uuids, ip, port, target):
    luns = []

    for uuid in uuids:
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


def get_nvmeof_uuids(ansible_vm):
    encoded = ansible_vm.slurp(src='/root/nvmeof_uuids.txt')['content']
    return [u.decode('utf-8') for u in base64.b64decode(encoded).splitlines()]


def get_nvmeof_connection_info(ansible_vm):
    encoded = ansible_vm.slurp(src='/root/nvmeof_connection.txt')['content']
    parts = base64.b64decode(encoded).decode('utf-8').strip().split()
    return {
        'nqn': parts[0],
        'address': parts[1],
        'port': int(parts[2]),
    }


def create_nvmeof_lun_sdk_entries(uuids, address, port, nqn):
    luns = []
    for uuid in uuids:
        lun = types.LogicalUnit(
            id=uuid,
            address=address,
            port=port,
            target=nqn,
        )
        luns.append(lun)
    return luns
