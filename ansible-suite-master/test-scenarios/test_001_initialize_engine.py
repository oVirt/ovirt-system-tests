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

from ost_utils.ansible.collection import engine_setup


def test_check_ansible_connectivity(ansible_engine, ansible_hosts):
    ansible_engine.ping()
    ansible_hosts.ping()


def test_initialize_engine(ansible_engine, engine_ip, engine_answer_file_path,
                           root_dir, ssh_key_file):
    engine_setup(
        ansible_engine,
        engine_ip,
        answer_file_path=engine_answer_file_path,
        ssh_key_path=ssh_key_file,
        ovirt_engine_setup_offline='true',
    )
