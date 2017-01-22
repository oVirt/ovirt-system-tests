#
# Copyright 2016-2017 Red Hat, Inc.
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
import nose.tools as nt

from ovirtsdk.xml import params

from ovirtlago import testlib

from test_utils import network_utils


DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

MANAGEMENT_NET = 'ovirtmgmt'

NIC_NAME = 'eth0'
VLAN200_IF_NAME = '{}.200'.format(NIC_NAME)

DEFAULT_MTU = 1500

VLAN200_NET = 'VLAN200_Network'
VLAN200_NET_IPv4_ADDR = '192.0.3.{}'
VLAN200_NET_IPv4_MASK = '255.255.255.0'
VLAN200_NET_IPv6_ADDR = '2001:0db8:85a3:0000:0000:574c:14ea:0a0{}'
VLAN200_NET_IPv6_MASK = '64'

VM0_NAME = 'vm0'


# appears in 003 as well... this doesn't really fit in network utils,
# should consider moving if/when a general utils module is ever introruced
def _hosts_in_cluster(api, cluster_name):
    hosts = api.hosts.list(query='cluster={}'.format(cluster_name))
    return sorted(hosts, key=lambda host: host.name)


@testlib.with_ovirt_api
def prepare_migration_vlan(api):
    usages = params.Usages(['migration'])

    nt.assert_true(
        network_utils.set_network_usages_in_cluster(api,
                                                    VLAN200_NET,
                                                    CLUSTER_NAME,
                                                    usages
                                                    )
    )

    # Set VLAN200's MTU to match the other VLAN's on the NIC.
    nt.assert_true(
        network_utils.set_network_mtu(api,
                                      VLAN200_NET,
                                      DC_NAME,
                                      DEFAULT_MTU)
    )


@testlib.with_ovirt_api
@testlib.with_ovirt_prefix
def migrate_vm(prefix, api):
    def current_running_host():
        host_id = api.vms.get(VM0_NAME).host.id
        return api.hosts.get(id=host_id).name

    src_host = current_running_host()
    dst_host = sorted([h.name() for h in prefix.virt_env.host_vms()
                       if h.name() != src_host])[0]

    migrate_params = params.Action(
        host=params.Host(
            name=dst_host
        ),
    )

    nt.assert_true(
      api.vms.get(VM0_NAME).migrate(migrate_params)
    )

    testlib.assert_true_within_short(
        lambda: api.vms.get(VM0_NAME).status.state == 'up'
    )

    nt.assert_equals(
        current_running_host(), dst_host
    )


@testlib.with_ovirt_api
def prepare_migration_attachments_ipv4(api):
    for index, host in enumerate(_hosts_in_cluster(api, CLUSTER_NAME),
                                 start=1):
        ip_address = VLAN200_NET_IPv4_ADDR.format(index)

        ip_configuration = network_utils.create_static_ip_configuration(
            ipv4_addr=ip_address,
            ipv4_mask=VLAN200_NET_IPv4_MASK)

        network_utils.attach_network_to_host(api,
                                             host,
                                             NIC_NAME,
                                             VLAN200_NET,
                                             ip_configuration)

        nt.assert_equals(
            host.nics.list(name=VLAN200_IF_NAME)[0].ip.address,
            ip_address)


@testlib.with_ovirt_api
def prepare_migration_attachments_ipv6(api):
    for index, host in enumerate(_hosts_in_cluster(api, CLUSTER_NAME),
                                 start=1):
        ip_address = VLAN200_NET_IPv6_ADDR.format(index)

        ip_configuration = network_utils.create_static_ip_configuration(
            ipv6_addr=ip_address,
            ipv6_mask=VLAN200_NET_IPv6_MASK)

        network_utils.modify_ip_config(api,
                                       host,
                                       VLAN200_NET,
                                       ip_configuration)

        # TODO: currently ost uses v3 SDK that doesn't report ipv6.
        # once available, verify address.


_TEST_LIST = [
    prepare_migration_vlan,

    prepare_migration_attachments_ipv4,
    migrate_vm,

    # TODO:
    # IPv6 migration is currently not working due to missing host ip6tables rules.
    # (https://bugzilla.redhat.com/1414524)
    # once resolved, uncomment the tests.

    # prepare_migration_attachments_ipv6,
    # migrate_vm,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
