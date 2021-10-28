#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging

import ansible_runner

from ost_utils.debuginfo_utils import obj_info
from ost_utils.ansible import private_dir as pd

LOGGER = logging.getLogger(__name__)


class ConfigBuilder:
    """This class prepares an ansible_runner.RunnerConfig instance.

    It's passed through several layers of functions and classes to finally
    be used in '_module_mapper.run_ansible'.
    """

    def __init__(self):
        self.inventory = None
        self.extravars = {"ansible_user": "root"}
        self.host_pattern = None
        self.module = None
        self.module_args = None

    def prepare(self):
        config = ansible_runner.RunnerConfig(
            inventory=self.inventory,
            extravars=self.extravars,
            host_pattern=self.host_pattern,
            module=self.module,
            module_args=self.module_args,
            private_data_dir=pd.PrivateDir.get(),
            quiet=True,
        )
        config.prepare()
        LOGGER.debug(f'ConfigBuilder prepare: {obj_info(config)}')
        return config

    def __str__(self):
        return (
            f'ConfigBuilder<inventory={self.inventory}, '
            f'host_pattern={self.host_pattern}, module={self.module}, '
            f'module_args={self.module_args}>'
        )
