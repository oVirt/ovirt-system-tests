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


def test_run_dig_loop(
    suite_dir,
    ansible_hosts,
):
    dig_loop_src_dir = os.path.join(suite_dir, 'dig_loop')
    ansible_hosts.copy(
        src=os.path.join(
            dig_loop_src_dir,
            'run_dig_loop.sh',
        ),
        dest='/usr/local/sbin',
        mode='preserve',
    )
    ansible_hosts.copy(
        src=os.path.join(
            dig_loop_src_dir,
            'rundigloop.service',
        ),
        dest='/etc/systemd/system',
    )
    ansible_hosts.systemd(
        daemon_reload='yes',
        name='rundigloop',
        state='started',
        enabled='yes',
    )


def test_he_deploy(
    root_dir,
    suite,
    ansible_host0,
    ansible_storage,
    he_host_name,
    he_mac_address,
    engine_ip,
):
    # not very nice. Better than duplicating whole file or symlinking though...
    if 'ssg' in suite:
        answer_file_src = os.path.join(
            root_dir,
            'common/answer-files/he-node-ng-ssg-suite-master.conf.in'
        )
    else:
        answer_file_src = os.path.join(
            root_dir,
            'common/answer-files/hosted-engine-deploy-answers-file.conf.in'
        )

    ansible_host0.copy(
        src=answer_file_src,
        dest='/root/hosted-engine-deploy-answers-file.conf.in'
    )

    setup_file_src = os.path.join(
        root_dir,
        'common/deploy-scripts/setup_first_he_host.sh'
    )
    ansible_host0.copy(src=setup_file_src, dest='/root/', mode='preserve')

    ansible_host0.shell(
        '/root/setup_first_he_host.sh '
        f'{he_host_name} '
        f'{he_mac_address} '
        f'{engine_ip}'
    )

    ansible_storage.shell('fstrim -va')


def test_add_engine_to_artifacts(artifacts, he_host_name, artifact_list):
    artifacts[he_host_name] = artifact_list
