# -*- coding: utf-8 -*-
#
# Copyright 2014, 2017, 2019 Red Hat, Inc.
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
from __future__ import absolute_import

import pytest

from os import environ, path

from ost_utils import assertions
from ost_utils import general_utils
from ost_utils.pytest import order_by
from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.engine import *
from ost_utils import utils

import logging
LOGGER = logging.getLogger(__name__)

def test_check_installed_packages(ansible_engine):
    working_dir='/tmp'
    script_file=os.path.join(
        os.environ.get('SUITE'), 'test-check-installed-packages.sh'
    )
    ansible_engine.copy(
        src=script_file,
        dest=f'{working_dir}/test-check-installed-packages.sh',
        mode='0755',
    )
    ansible_engine.shell(
        f'{working_dir}/test-check-installed-packages.sh'
    )

