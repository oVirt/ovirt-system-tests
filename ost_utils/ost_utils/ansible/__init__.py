#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

"""Convenience functions for ansible runner.

This module provides a couple of helpers that make running ansible modules
with ansible runner more pleasant. An example of direct usage of ansible
runner:

    import ansible_runner
    r = ansible_runner.run(
        private_data_dir='/tmp/demo',
        host_pattern='localhost',
        module='shell',
        module_args='whoami'
    )

    if r.status == 'failed':
        pass  # handle failure

Can be written with the utils provided as:

    localhost = ModuleMapper('inventory', 'localhost')
    localhost.shell(cmd='whoami')

which will raise 'AnsibleExecutionError' on failure.

"""

# flake8: noqa
from ost_utils.ansible.logs_collector import LogsCollector
from ost_utils.ansible.module_mappers import AnsibleExecutionError
