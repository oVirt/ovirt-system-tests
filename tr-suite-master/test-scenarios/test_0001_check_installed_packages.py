#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

from os import environ, path

from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.env import suite_dir

def test_check_installed_packages(ansible_engine, suite_dir):
    working_dir = '/usr/local/bin'
    func = "func.sh"
    script = 'test-check-installed-packages.sh'

    src_script_file=os.path.join(
        suite_dir, func
    )
    dst_script_file=os.path.join(
        working_dir, func
    )
    ansible_engine.copy(
        src=src_script_file,
        dest=dst_script_file,
        mode='0755'
    )
    src_script_file=os.path.join(
        suite_dir, script
    )
    dst_script_file=os.path.join(
        working_dir, script
    )
    ansible_engine.copy(
        src=src_script_file,
        dest=dst_script_file,
        mode='0755'
    )
    ansible_engine.shell(
        f'{dst_script_file} '
        f'-w {working_dir}'
    )
