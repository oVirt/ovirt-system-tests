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
def deploy(ansible_all, deploy_scripts, working_dir, request):
    if deployment_utils.is_deployed(working_dir):
        LOGGER.info("Environment already deployed")
        return

    LOGGER.info("Waiting for SSH on the VMs")
    ansible_all.wait_for_connection(timeout=120)

    # disable all repos
    package_mgmt.disable_all_repos(ansible_all)

    # dnf is grumpy when it has no repos to work with
    package_mgmt.add_dummy_repo(ansible_all)

    # add custom repos
    custom_repos = request.config.getoption('--custom-repo')
    if custom_repos is not None:
        custom_repos = package_mgmt.expand_jenkins_repos(custom_repos)
        package_mgmt.add_custom_repos(ansible_all, custom_repos)
        ansible_all.shell(
            'dnf upgrade --nogpgcheck -y -x ovirt-release-master'
        )
        # check if packages from custom repos were used
        if not request.config.getoption('--skip-custom-repos-check'):
            package_mgmt.check_installed_packages(ansible_all)

    # report package versions
    package_mgmt.report_ovirt_packages_versions(ansible_all)

    # run deployment scripts
    runs = [functools.partial(run_scripts, hostname, scripts)
            for hostname, scripts in deploy_scripts.items()]
    utils.invoke_different_funcs_in_parallel(*runs)

    # mark env as deployed
    deployment_utils.mark_as_deployed(working_dir)
