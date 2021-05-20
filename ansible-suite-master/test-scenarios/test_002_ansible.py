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

import os


def test_ansible_run(suite_dir, ansible_engine, ansible_inventory):
    ansible_run_dir = '/tmp/ansible_run'

    for dir_name in ['inventory', 'env']:
        ansible_engine.file(
            path=f'{ansible_run_dir}/{dir_name}',
            state='directory',
            recurse='yes'
        )

    ansible_role_src = os.path.join(suite_dir, 'ovirt-deploy')
    ansible_engine.copy(
        src=ansible_role_src,
        dest=ansible_run_dir,
    )

    ansible_playbook = os.path.join(suite_dir, 'engine.yml')
    ansible_engine.copy(
        src=ansible_playbook,
        dest=f'{ansible_run_dir}/engine.yml',
    )

    ansible_engine.copy(
        src=ansible_inventory.dir,
        dest=f'{ansible_run_dir}/inventory/hosts',
    )

    ansible_engine.copy(
        src=os.environ.get('OST_IMAGES_SSH_KEY'),
        dest=f'{ansible_run_dir}/env/ssh_key',
    )

    ansible_engine.shell(
        f'ansible-runner -vvv --playbook engine.yml run {ansible_run_dir}'
    )
