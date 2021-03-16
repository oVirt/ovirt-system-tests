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
import logging
import pytest

from collections import namedtuple

from ost_utils import backend
from ost_utils.ansible import AnsibleExecutionError

LOGGER = logging.getLogger(__name__)
REPO_NAME = 'extra-src-'

Package = namedtuple('Package', ['name', 'version', 'repo'])


@pytest.fixture(scope="session", autouse=True)
def check_installed_packages(ansible_by_hostname):
    vms_pckgs_dict_list = []
    for hostname in backend.default_backend().hostnames():
        vm_pckgs_dict = _get_custom_repos_packages(
            ansible_by_hostname(hostname))
        LOGGER.info(f'packages installed on {hostname}: \n{vm_pckgs_dict}\n')
        vms_pckgs_dict_list.append(vm_pckgs_dict)
    if all(_check_if_user_specified_repos(pckgs_dict) and
           _check_if_no_packages_used(pckgs_dict) for pckgs_dict in
           vms_pckgs_dict_list):
        raise RuntimeError('None of user custom repos has been used')
    yield


def _get_custom_repos_packages(ansible_vm):
    installed_packages = {}
    for repo_no in range(1, 100):
        repo_name = f'{REPO_NAME}{repo_no}'
        try:
            installed_packages[repo_name] = _get_installed_packages(ansible_vm,
                                                                    repo_name)

        except AnsibleExecutionError as e:
            if 'Error: Unknown repo' in str(e):
                break
            raise
    return installed_packages


def _get_installed_packages(ansible_vm, repo_name):
    # dnf adapts its output to the width of the terminal.
    # If it fails to find this width out (which it does using:
    # fcntl.ioctl(fd, termios.TIOCGWINSZ, buf)
    # ), it defaults to 80 chars.
    # If a package name + version + repo is wider than that, it will
    # split the output across more than one line.
    # This breaks our simplistic parsing. To work around this,
    # call 'stty cols' to tell it that the terminal is wide.
    # A better solution, one day, might be to make dnf support outputting
    # such information in JSON, and parse this json if/where needed.
    ansible_res = ansible_vm.shell(f'stty cols 300; dnf repo-pkgs {repo_name} list installed')
    result = [(line.split()) for line in ansible_res['stdout'].split('\n')]
    filter_results(result)
    return [
        Package(*line) for line in result
    ]


def filter_results(result):
    try:
        indx = result.index(['Installed', 'Packages'])
    except ValueError:
        return result.clear()
    del result[0:indx+1]


def _check_if_no_packages_used(pckgs_dict):
    return all(not pckgs_list for pckgs_list in pckgs_dict.values())


def _check_if_user_specified_repos(pckgs_dict):
    return bool(pckgs_dict.keys())
