#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging

from ost_utils import he_utils


def test_local_maintenance(ansible_host0, ansible_by_hostname):
    logging.info('Waiting For System Stability...')
    he_utils.wait_until_engine_vm_is_not_migrating(ansible_host0)

    non_he_host_name = he_utils.host_names_not_running_he_vm(ansible_host0)[0]
    non_he_host = ansible_by_hostname(non_he_host_name)

    ret = non_he_host.shell('hosted-engine --set-maintenance --mode=local')
    assert ret['rc'] == 0

    ret = non_he_host.shell('hosted-engine --set-maintenance --mode=none')
    assert ret['rc'] == 0
