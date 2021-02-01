#
# Copyright 2019 Red Hat, Inc.
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
import contextlib
import os

from ovirtlago import testlib  # pylint: disable=import-error

# FIXME This hack is needed until we have proper support for IPv6 from lago
# Issue to track the Lago IPv6 https://github.com/lago-project/lago/issues/770

IPV6_NETPREFIX = 'fd8f:1391:3a82:' + os.getenv('IPV6_SUBNET', '')
HOST0_IPV6_ADDRESS = IPV6_NETPREFIX + '::' + '100'
HOST1_IPV6_ADDRESS = IPV6_NETPREFIX + '::' + '101'
STORAGE_IPV6_ADDRESS = IPV6_NETPREFIX + '::' + '200'
ENGINE_IPV6_ADDRESS = IPV6_NETPREFIX + '::' + '250'
IPV6_ONLY = os.getenv('IPV6_ONLY', False)


def open_connection_to_api_with_ipv6_on_relevant_suite():
    if IPV6_ONLY:
        prefix = testlib.get_test_prefix()
        engine_vm = prefix.virt_env.engine_vm()
        with _create_url_from_ipv6_for_api(
                prefix,
                testlib.get_prefixed_name('engine')
        ):
            engine_vm.get_api(api_ver=4)
            engine_vm.get_api()


@contextlib.contextmanager
def _create_url_from_ipv6_for_api(prefix, host_name):
    mgmt_net = prefix.virt_env.get_net()
    ip_addr = prefix.virt_env.get_vm(host_name).ip()
    mgmt_net.add_mapping(host_name, '[%s]' % ip_addr)
    try:
        yield
    finally:
        mgmt_net.add_mapping(host_name, ip_addr)
