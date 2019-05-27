# Copyright 2018-9 Red Hat, Inc.
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
import errno
import shutil

import pytest

from ovirtlib import syncutil

from fixtures.engine import ENGINE_DOMAIN
from fixtures.engine import ANSWER_FILE_SRC
from fixtures.host import HOST_0_DOMAIN

HOSTS_FILE = '/etc/hosts'


class EngineNotResorvableError(Exception):
    pass


@pytest.fixture(scope='session')
def fqdn(env):
    BACKUP_FILE = HOSTS_FILE + 'OST-BACKUP'

    address = env.get_vms()[ENGINE_DOMAIN].ip()
    fqdn = _fetch_fqdn(ANSWER_FILE_SRC)

    remove_backup = False
    if not _fqdn_in_hosts_file(fqdn, address):
        try:
            shutil.copy2(HOSTS_FILE, BACKUP_FILE)
        except OSError as err:
            if err.errno == errno.EACCES:
                raise EngineNotResorvableError
            raise
        remove_backup = True
        _modify_hosts_file(fqdn, address)
    yield
    if remove_backup:
        shutil.move(BACKUP_FILE, HOSTS_FILE)


def _fqdn_in_hosts_file(fqdn, address):
    with open(HOSTS_FILE) as f:
        for line in f:
            line = line.split("#", 1)[0]
            args = line.split()
            if not args:
                continue
            addr = args[0]
            hostnames = args[1:]
            if addr == address and fqdn in hostnames:
                return True
    return False


def _fetch_fqdn(answer_file):
    FQDN_ENTRY = 'OVESETUP_CONFIG/fqdn'

    with open(answer_file) as f:
        for line in f:
            if line.startswith(FQDN_ENTRY):
                return line.strip().split(':', 1)[1]


def _modify_hosts_file(fqdn, address):
    TEMP_FILE = HOSTS_FILE + 'OST-TMP'
    TEMP_OST_ENTRY = '# temporary OST entry'
    ENGINE_ENTRY = ' '.join([address, fqdn, TEMP_OST_ENTRY]) + '\n'

    shutil.copy2(HOSTS_FILE, TEMP_FILE)
    with open(TEMP_FILE, 'r+') as tf:
        data = tf.read()
        tf.seek(0, 0)
        tf.write(ENGINE_ENTRY + data)

    shutil.move(TEMP_FILE, HOSTS_FILE)


@pytest.fixture(scope='session')
def host0_eth2_ipv6(env):
    """
    nics created by lago are managed by nmcli and have autoconf ipv6 but have
    not been assigned an address. this function requests a dynamic assignment
    of an ipv6 to 'eth2' and retrieves it.
    :return: the ipv6 address as string
    :raise: timeout exception if global ipv6 address not found on NIC
    """
    host_0 = env.get_vms()[HOST_0_DOMAIN]
    return _enable_dynamic_ipv6(host_0, 'eth2')


@pytest.fixture(scope='session')
def host0_eth1_ipv6(env):
    """
    nics created by lago are managed by nmcli and have autoconf ipv6 but have
    not been assigned an address. this function requests a dynamic assignment
    of an ipv6 to 'eth1' and retrieves it.
    :return: the ipv6 address as string
    :raise: timeout exception if global ipv6 address not found on NIC
    """
    host_0 = env.get_vms()[HOST_0_DOMAIN]
    return _enable_dynamic_ipv6(host_0, 'eth1')


@pytest.fixture(scope='session')
def engine_storage_ipv6(env):
    """
    lago creates a network with an ipv6 subnet and connects it to NIC
    'eth1' of the engine. It names the network 'storage' but does not assign an
    ipv6 address to the NIC.
    this function requests a dynamic assignment of an ipv6 to 'eth1' of the
    engine machine and retrieves it.
    :return: the ipv6 address as string
    :raise: timeout exception if global ipv6 address not found on NIC
    """
    engine = env.get_vms()[ENGINE_DOMAIN]
    ENGINE_STORAGE_NIC = 'eth1'
    return _enable_dynamic_ipv6(engine, ENGINE_STORAGE_NIC)


def _enable_dynamic_ipv6(lago_host, nic_name):
    """
    this function connects to the specified lago VM using its ssh API to:
    * request the host OS to dynamically assign an ipv6 address to the
      specified NIC
    * wait for the address to be assigned (it might take up to a few seconds)
    * retrieve the address
    :return: the ipv6 address as string
    :raise: timeout exception if global ipv6 address not found on NIC
    """
    _assign_ipv6(lago_host, nic_name)
    return syncutil.sync(exec_func=_get_ipv6,
                         exec_func_args=(lago_host, nic_name),
                         success_criteria=lambda ipv6: ipv6 != '',
                         timeout=10)


def _assign_ipv6(lago_vm, nic_name):
    """
    lago creates ipv6 subnets and sets ipv6 autoconf on its VMs' NICs but does
    not assign ipv6 addresses to the NICs.
    this function connects to a lago VM using its ssh API and requests an ipv6
    address be assigned to the NIC using nmcli.
    :param lago_vm: any lago vm that exposes an ssh API into itself
    :param nic_name: the name of the NIC to assign an ipv6 address to
    :raise: exception if an error occurred during the assignment
    """
    res = lago_vm.ssh(['nmcli', 'con', 'modify',
                       nic_name, 'ipv6.method', 'auto'])
    if res.code:
        raise Exception('nmcli con modify failed: exit code %s, error "%s"'
                        % (res.code, res.err))
    res = lago_vm.ssh(['nmcli', 'con', 'up', nic_name])
    if res.code:
        raise Exception('nmcli con up failed: exit code %s, error "%s"'
                        % (res.code, res.err))


def _get_ipv6(lago_vm, nic_name):
    """
    :param lago_vm: any lago vm that exposes an ssh API into itself
    :param nic_name: the name of the NIC from which to get the ipv6 address
    :return: the ipv6 address of the lago vm on eth1 as string or empty string
    """
    INET6 = 'inet6 '
    res = lago_vm.ssh(['ip -o -6 a show', nic_name, 'scope global'])
    return res.out[res.out.find(INET6) + len(INET6):res.out.find('/')]
