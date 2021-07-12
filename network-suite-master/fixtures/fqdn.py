# Copyright 2018-2021 Red Hat, Inc.
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
import pytest

from ovirtlib import sshlib
from ovirtlib import syncutil

OVN_CONF = '/etc/ovirt-provider-ovn/conf.d/10-setup-ovirt-provider-ovn.conf'


class EngineNotResorvableError(Exception):
    pass


@pytest.fixture(scope='session')
def ovirt_provider_ovn_with_ip_fqdn(ovirt_engine_service_up, engine_facts,
                                    engine_answer_file_path):
    provider_ip = f'provider-host={engine_facts.default_ip(urlize=True)}'
    provider_fqdn = f'provider-host={_fetch_fqdn(engine_answer_file_path)}'
    engine = sshlib.Node(engine_facts.default_ip())
    try:
        engine.global_replace_str_in_file(provider_fqdn, provider_ip, OVN_CONF)
        engine.restart_service('ovirt-provider-ovn')
        yield
    finally:
        engine.global_replace_str_in_file(provider_ip, provider_fqdn, OVN_CONF)
        engine.restart_service('ovirt-provider-ovn')


def _fetch_fqdn(answer_file):
    FQDN_ENTRY = 'OVESETUP_CONFIG/fqdn'

    with open(answer_file) as f:
        for line in f:
            if line.startswith(FQDN_ENTRY):
                return line.strip().split(':', 1)[1]


@pytest.fixture(scope='session')
def host0_eth2_ipv6(host0_facts):
    """
    nics created by lago are managed by nmcli and have autoconf ipv6 but have
    not been assigned an address. this function requests a dynamic assignment
    of an ipv6 to 'eth2' and retrieves it.
    :return: the ipv6 address as string
    :raise: timeout exception if global ipv6 address not found on NIC
    """
    host_0 = sshlib.Node(host0_facts.default_ip(), host0_facts.ssh_password)
    return _enable_dynamic_ipv6(host_0, 'eth2')


@pytest.fixture(scope='session')
def host0_eth1_ipv6(host0_facts):
    """
    nics created by lago are managed by nmcli and have autoconf ipv6 but have
    not been assigned an address. this function requests a dynamic assignment
    of an ipv6 to 'eth1' and retrieves it.
    :return: the ipv6 address as string
    :raise: timeout exception if global ipv6 address not found on NIC
    """
    host_0 = sshlib.Node(host0_facts.default_ip(), host0_facts.ssh_password)
    return _enable_dynamic_ipv6(host_0, 'eth1')


@pytest.fixture(scope='session')
def engine_storage_ipv6(engine_facts):
    """
    lago creates a network with an ipv6 subnet and connects it to NIC
    'eth1' of the engine. It names the network 'storage' but does not assign an
    ipv6 address to the NIC.
    this function requests a dynamic assignment of an ipv6 to 'eth1' of the
    engine machine and retrieves it.
    :return: the ipv6 address as string
    :raise: timeout exception if global ipv6 address not found on NIC
    """
    engine = sshlib.Node(engine_facts.default_ip(), engine_facts.ssh_password)
    ENGINE_STORAGE_NIC = 'eth1'
    return _enable_dynamic_ipv6(engine, ENGINE_STORAGE_NIC)


def _enable_dynamic_ipv6(ssh_node, nic_name):
    """
    this function connects to the specified lago VM using its ssh API to:
    * request the host OS to dynamically assign an ipv6 address to the
      specified NIC
    * wait for the address to be assigned (it might take up to a few seconds)
    * retrieve the address
    :return: the ipv6 address as string
    :raise: timeout exception if global ipv6 address not found on NIC
    """
    _assign_ipv6(ssh_node, nic_name)
    return syncutil.sync(exec_func=_get_ipv6,
                         exec_func_args=(ssh_node, nic_name),
                         success_criteria=lambda ipv6: ipv6 != '',
                         timeout=10)


def _assign_ipv6(ssh_node, nic_name):
    """
    lago creates ipv6 subnets and sets ipv6 autoconf on its VMs' NICs but does
    not assign ipv6 addresses to the NICs.
    this function connects to a lago VM using its ssh API and requests an ipv6
    address be assigned to the NIC using nmcli.
    :param ssh_node: an sshlib.Node that exposes an ssh API into itself
    :param nic_name: the name of the NIC to assign an ipv6 address to
    :raise: exception if an error occurred during the assignment
    """
    res = ssh_node.exec_command(
        ' '.join(['nmcli', 'con', 'modify', nic_name, 'ipv6.method', 'auto'])
    )

    if res.code:
        raise Exception('nmcli con modify failed: exit code %s, error "%s"'
                        % (res.code, res.err))
    res = ssh_node.exec_command(' '.join(['nmcli', 'con', 'up', nic_name]))
    if res.code:
        raise Exception('nmcli con up failed: exit code %s, error "%s"'
                        % (res.code, res.err))


def _get_ipv6(ssh_node, nic_name):
    """
    :param ssh_node: an sshlib.Node that exposes an ssh API into itself
    :param nic_name: the name of the NIC from which to get the ipv6 address
    :return: the ipv6 address of the lago vm on eth1 as string or empty string
    """
    INET6 = 'inet6 '
    res = ssh_node.exec_command(['ip -o -6 a show', nic_name, 'scope global'])
    return res.out[res.out.find(INET6) + len(INET6):res.out.find('/')]
