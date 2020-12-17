#
# Copyright 2020 Red Hat, Inc.
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
import itertools
import os
import shutil
import tempfile
import threading


class PrivateDir:
    """Creates private directories for ansible_runner

    ansible_runner requires providing a path to a "private directory".
    It uses the private directory to cache stuff.

    When 2 different tests ask for some VM facts, it's good to use the same
    private directory for both calls. If we don't do that, we'll be gathering
    facts about the VMs every time, which would slow down OST noticeably.

    There's one quirk with this approach - if someone tries to query VM
    facts from 2 different threads at once, ansible_runner will fail
    saying that "the private directory should not exist". That's why we need
    to have one private directory per thread.

    """

    thread_local = threading.local()
    all_dirs = set()

    @classmethod
    def get(cls):
        if 'dir' not in cls.thread_local.__dict__:
            path = tempfile.mkdtemp()
            cls.thread_local.__dict__['dir'] = path
            cls.all_dirs.add(path)
        return cls.thread_local.__dict__['dir']

    @classmethod
    def event_data_files(cls):
        return itertools.chain.from_iterable(
            glob.iglob(os.path.join(dir, "artifacts/*/job_events/*.json"))
            for dir in cls.all_dirs
        )

    @classmethod
    def cleanup(cls):
        for dir in cls.all_dirs:
            shutil.rmtree(dir)
        cls.all_dirs.clear()
