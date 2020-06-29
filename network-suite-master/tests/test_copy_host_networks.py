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
import pytest

from ovirtlib import hostlib

from testlib import suite


@suite.skip_suites_below(4.4)
def test_copy_host_networks(configured_hosts):
    source_host = configured_hosts[0]
    destination_host = configured_hosts[1]

    destination_host.copy_networks_from(source_host)
    assert source_host.compare_nics_except_mgmt(
        destination_host, CopyHostComparator.compare
    )


@pytest.fixture(
    scope='function', params=[('one', 'one')], ids=['scenario_one_to_one'],
)
def configured_hosts(request, host_scenarios, host_0_up, host_1_up):
    source_attach_data = host_scenarios[request.param[0]]
    destination_attach_data = host_scenarios[request.param[1]]

    with hostlib.setup_networks(
        host_0_up, source_attach_data
    ), hostlib.setup_networks(
        host_1_up, destination_attach_data
    ):
        yield (host_0_up, host_1_up)


@pytest.fixture(scope='module')
def host_scenarios():
    return {
        'one': [],
    }


class CopyHostComparator(object):
    """
    nic0: source nic
    nic1: destination nic
    """

    @staticmethod
    def compare(nic0, nic1):
        return (
            CopyHostComparator._neither_has_network_attached(nic0, nic1)
        ) or (
            nic0.is_same_network_attachment(nic1)
            and CopyHostComparator._network_attachment_correctly_copied(
                nic0, nic1)
        )

    @staticmethod
    def _neither_has_network_attached(nic0, nic1):
        return (
            not nic0.is_network_attached()
            and nic1.is_same_network_attachment(nic0)
        )

    @staticmethod
    def _network_attachment_correctly_copied(nic0, nic1):
        return (
            CopyHostComparator._non_static_ipv4_copied(nic0, nic1)
            or CopyHostComparator._ipv4_static_protocol_disabled(nic0, nic1)
        ) and (
            CopyHostComparator._non_static_ipv6_copied(nic0, nic1)
            or CopyHostComparator._ipv6_static_protocol_disabled(nic0, nic1)
        )

    @staticmethod
    def _non_static_ipv4_copied(nic0, nic1):
        return not nic0.is_static_ipv4() and nic0.boot_protocol_equals(nic1)

    @staticmethod
    def _ipv4_static_protocol_disabled(nic0, nic1):
        """
        Copying network configurations that contain static IPs is not possible.
        In such cases the resulting boot protocol should be disabled.
        """
        return nic0.is_static_ipv4() and nic1.is_disabled_ipv4()

    @staticmethod
    def _non_static_ipv6_copied(nic0, nic1):
        return (
            not nic0.is_static_ipv6()
            and nic0.ipv6_boot_protocol_equals(nic1)
        )

    @staticmethod
    def _ipv6_static_protocol_disabled(nic0, nic1):
        """
        Copying network configurations that contain static IPs is not possible.
        In such cases the resulting boot protocol should be disabled.
        """
        return nic0.is_static_ipv6() and nic1.is_disabled_ipv6()
