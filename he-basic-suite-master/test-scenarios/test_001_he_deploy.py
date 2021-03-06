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

from ost_utils import backend


def test_he_deploy(suite_dir, ansible_host0, ansible_storage):
    answer_file_src = os.path.join(suite_dir, 'answers.conf.in')
    ansible_host0.copy(
        src=answer_file_src,
        dest='/root/hosted-engine-deploy-answers-file.conf.in'
    )

    setup_file_src = os.path.join(suite_dir, 'setup_first_he_host.sh')
    ansible_host0.copy(src=setup_file_src, dest='/root/', mode='preserve')

    he_name = backend.default_backend().engine_hostname()
    ansible_host0.shell(f'/root/setup_first_he_host.sh {he_name}')

    ansible_storage.shell('fstrim -va')
