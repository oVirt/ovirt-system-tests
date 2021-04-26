# -*- coding: utf-8 -*-
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

from os import path

from ost_utils.ansible import module_mappers


LOGGER = logging.getLogger(__name__)


def run_scripts(hostname, scripts):
    ansible_handle = module_mappers.module_mapper_for(hostname)
    for script in scripts:
        expanded = path.expandvars(script)
        LOGGER.info(f"Running {expanded} on {hostname}")
        ansible_handle.script(expanded)
