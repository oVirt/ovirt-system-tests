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
from ovirtlib import hostlib
from ovirtlib import netattachlib
from ovirtlib import sshlib
from ovirtlib import syncutil
from testlib import suite

BOND_NAME = 'bond0'
SLAVE1 = 'eth2'
SLAVE2 = 'eth3'


class ActiveSlaveNotChangedError(Exception):
    pass


@suite.skip_suites_below('4.4')
@suite.xfail_suite_master(reason='BZ 1846338',
                          raises=ActiveSlaveNotChangedError)
def test_bond_active_slave(system, default_data_center, default_cluster,
                           host_0_up):
    bond_data = netattachlib.ActiveSlaveBonding(
        BOND_NAME, slave_names=(SLAVE1, SLAVE2)
    )
    with hostlib.setup_networks(host_0_up, bonding_data=(bond_data,)):
        bond = hostlib.Bond(host_0_up)
        bond.import_by_name(BOND_NAME)
        bond.wait_for_up_status()
        initial_active_slave = bond.active_slave
        inactive_slave = bond.inactive_slaves[0]
        sshlib.Node(
            host_0_up.address, host_0_up.root_password
        ).change_active_slave(BOND_NAME, inactive_slave.name)
        try:
            syncutil.sync(
                exec_func=lambda: bond.active_slave,
                exec_func_args=(),
                success_criteria=lambda active_slave:
                    active_slave.id != initial_active_slave.id,
                timeout=10
            )
        except syncutil.Timeout:
            raise ActiveSlaveNotChangedError(
                'active slave: {} initial active slave: {}'.format(
                    bond.active_slave.name, initial_active_slave.name
                )
            )
