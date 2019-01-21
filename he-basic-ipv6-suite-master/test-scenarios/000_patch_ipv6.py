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
from ovirtlago import testlib
from test_utils import ipv6_utils


@testlib.with_ovirt_prefix
def replace_ipv4_with_ipv6_addresses(prefix):
    mgmt_net = prefix.virt_env.get_net()
    mgmt_net.add_mapping(testlib.get_prefixed_name('engine'),
                         ipv6_utils.ENGINE_IPV6_ADDRESS)
    mgmt_net.add_mapping(testlib.get_prefixed_name('host-0'),
                         ipv6_utils.HOST0_IPV6_ADDRESS)
    mgmt_net.add_mapping(testlib.get_prefixed_name('host-1'),
                         ipv6_utils.HOST1_IPV6_ADDRESS)
    mgmt_net.add_mapping(testlib.get_prefixed_name('storage'),
                         ipv6_utils.STORAGE_IPV6_ADDRESS)


_TEST_LIST = [
    replace_ipv4_with_ipv6_addresses,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
