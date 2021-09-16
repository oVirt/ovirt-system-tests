#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

from fixtures.host import ETH2
from fixtures.host import ETH3

from ovirtlib import hostlib
from ovirtlib import netattachlib
from ovirtlib import sshlib
from ovirtlib import syncutil
from testlib import suite

BOND_NAME = 'bond0'


class ActiveSlaveNotChangedError(Exception):
    pass


@suite.skip_suites_below('4.4')
def test_bond_active_slave(system, default_data_center, default_cluster,
                           host_0_up):
    bond_data = netattachlib.ActiveSlaveBonding(
        BOND_NAME, slave_names=(ETH2, ETH3)
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
