#
# Copyright 2014-2020 Red Hat, Inc.
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

import logging
import time

from ost_utils import he_utils

WAIT_VALUE = 300


def test_local_maintenance(ansible_host0, ansible_by_hostname):
    logging.info('Waiting For System Stability...')
    # TODO: Replace arbitrary sleep with something more sensible
    time.sleep(WAIT_VALUE)

    non_he_host_name = he_utils.host_names_not_running_he_vm(ansible_host0)[0]
    non_he_host = ansible_by_hostname(non_he_host_name)

    ret = non_he_host.shell('hosted-engine --set-maintenance --mode=local')
    assert ret['rc'] == 0

    ret = non_he_host.shell('hosted-engine --set-maintenance --mode=none')
    assert ret['rc'] == 0
