#
# Copyright 2017 Red Hat, Inc.
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

import glob
import os
import subprocess
import ConfigParser
from ovirtlago import (testlib, constants)


@testlib.with_ovirt_prefix
def gen_config_file_and_params(prefix, cfg_in, cfg_out, cfg_path):
    """Parse reposync config file and prepare params for repoclosure

    :param file cfg_in:     Reposync config file object to adjust
    :param file cfg_out:    File object to write adjusted configuration into
    :param str  cfg_path:   The actual path to the reposync config

    :rtype: list
    :returns: A list with 'repoclosure' command including it's parameters
    """
    TEST_REPO_SECTION = 'internal_repo'
    command = ['repoclosure', '-t', '--config={}'.format(cfg_path)]
    internal_repo_ip = prefix.virt_env.get_net().gw()
    internal_repo_port = constants.REPO_SERVER_PORT
    internal_repo_url = 'http://{ip}:{port}/el7/'.format(
        ip=internal_repo_ip, port=internal_repo_port
    )

    config = ConfigParser.ConfigParser()
    config.readfp(cfg_in)
    for section in config.sections():
        if section == "main":
            continue
        command.append('--lookaside={}'.format(section))
        if config.has_option(section, 'exclude'):
            config.remove_option(section, 'exclude')
        if config.has_option(section, 'includepkgs'):
            config.remove_option(section, 'includepkgs')

    config.add_section(TEST_REPO_SECTION)
    config.set(TEST_REPO_SECTION, 'name', 'Local repo')
    config.set(TEST_REPO_SECTION, 'baseurl', internal_repo_url)
    config.set(TEST_REPO_SECTION, 'enabled', 1)
    config.set(TEST_REPO_SECTION, 'gpgcheck', 0)
    config.set(TEST_REPO_SECTION, 'proxy', '_none_')
    command.append('--repoid={}'.format(TEST_REPO_SECTION))
    config.write(cfg_out)
    return command


def reposync_config_file(config):
    """Open a config file for read and write in order to modify it
    :param str config:  reposync config filename

    :rtype: list
    :returns: A repoclosure command with all the needed parameters ready to be
    executed
    """
    repoclosure_conf = config + "_repoclosure"
    with open(config, 'r') as rf:
        with open(repoclosure_conf, 'w') as wf:
            command = gen_config_file_and_params(rf, wf, repoclosure_conf)
            wf.truncate()
    return command


def check_repo_closure():
    """Find reposync config file(s) and check repoclosure against the internal
     repo with the repos in the config(s) as lookaside repos
    """
    configs = glob.glob(
        os.path.join(os.environ.get('SUITE'), '*reposync*.repo')
    )
    if not configs:
        raise RuntimeError("Could not find reposync config file.")
    for config in configs:
        command = reposync_config_file(config)
        try:
            subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            err_msg = ("\n"
                       "## Params: {com}.\n"
                       "## Exist status: {es}\n"
                       "## Output: {out}\n\n"
                       ).format(com=e.cmd, es=e.returncode, out=e.output,)
            raise RuntimeError(err_msg)


_TEST_LIST = [
    check_repo_closure,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
