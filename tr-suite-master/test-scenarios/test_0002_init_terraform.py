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

def test_init_terraform(ansible_engine, suite_dir):
    pytest.skip('Skip terraform')
    plugin_dir = '/usr/local/bin'
    script = 'test-init-terraform.sh'

    src_script_file=os.path.join(
        suite_dir, script
    )
    dst_script_file=os.path.join(
        plugin_dir, script
    )
    ansible_engine.copy(
        src=src_script_file,
        dest=dst_script_file,
        mode='0755'
    )
    ansible_engine.shell(
        f'{dst_script_file} '
        f'-l {plugin_dir} '
    )
