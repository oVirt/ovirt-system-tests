#
# Copyright 2021 Red Hat, Inc.
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

import functools
import logging
import pytest

from ost_utils import deployment_utils
from ost_utils import utils
from ost_utils.deployment_utils import package_mgmt
from ost_utils.deployment_utils.scripts import run_scripts


LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def deploy(all_hostnames, deploy_scripts, working_dir):
    if deployment_utils.is_deployed(working_dir):
        LOGGER.info("Environment already deployed")
        return

    # run deployment scripts
    runs = [functools.partial(run_scripts, hostname, scripts)
            for hostname, scripts in deploy_scripts.items()]
    utils.invoke_different_funcs_in_parallel(*runs)
    package_mgmt.check_installed_packages(all_hostnames)

    # mark env as deployed
    deployment_utils.mark_as_deployed(working_dir)
