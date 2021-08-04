#
# Copyright 2020-2021 Red Hat, Inc.
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

import ansible_runner

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
        LOGGER.debug(f'ConfigBuilder prepare: {config}')
        return config

    def __str__(self):
        return (
            f'ConfigBuilder<inventory={self.inventory}, '
            f'host_pattern={self.host_pattern}, module={self.module}, '
            f'module_args={self.module_args}>'
        )
