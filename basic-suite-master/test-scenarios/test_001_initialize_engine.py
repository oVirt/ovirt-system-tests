#
# Copyright 2014-2021 Red Hat, Inc.
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

import os

from ost_utils.ansible.collection import engine_setup


def test_initialize_engine(
    engine_ip, ansible_engine, engine_answer_file_path, ssh_key_file
):
    if os.environ.get('ENABLE_DEBUG_LOGGING'):
        ansible_engine.shell(
            'sed -i '
            '-e "/.*logger category=\\"org.ovirt\\"/{ n; s/INFO/DEBUG/ }" '
            '-e "/.*logger category=\\"org.ovirt.engine.core.bll\\"/{ n; s/INFO/DEBUG/ }" '
            '-e "/.*<root-logger>/{ n; s/INFO/DEBUG/ }" '
            '/usr/share/ovirt-engine/services/ovirt-engine/ovirt-engine.xml.in'
        )

    engine_setup(
        ansible_engine,
        engine_ip,
        answer_file_path=engine_answer_file_path,
        ssh_key_path=ssh_key_file,
        ovirt_engine_setup_offline='true',
        ovirt_engine_setup_engine_configs=[
            {'key': 'VdsLocalDisksLowFreeSpace', 'value': '400'},
            {'key': 'OvfUpdateIntervalInMinutes', 'value': '10'},
            {'key': 'ServerRebootTimeout', 'value': '120'},
            {'key': 'ClientModeVncDefault', 'value': 'NoVnc'},
        ],
    )
    ansible_engine.shell('ss -anp')

    ansible_engine.systemd(name='ovirt-engine-notifier', state='started')
    ansible_engine.systemd(name='ovirt-engine', state='started')
    ansible_engine.systemd(name='ovirt-engine-dwhd', state='started')
