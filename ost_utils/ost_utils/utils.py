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

import fcntl
import functools
import logging
import os
import queue
import sys
import threading

LOGGER = logging.getLogger(__name__)


def _ret_via_queue(func, queue):
    try:
        queue.put({'return': func()})
    except Exception:
        LOGGER.debug(
            'Error while running thread %s',
            threading.current_thread().name,
            exc_info=True
        )
        queue.put({'exception': sys.exc_info()})


def func_vector(target, args_sequence):
    return [functools.partial(target, *args) for args in args_sequence]


class VectorThread:
    def __init__(self, targets):
        self.targets = targets
        self.results = None

    def start_all(self):
        self.thread_handles = []
        for target in self.targets:
            q = queue.Queue()
            t = threading.Thread(target=_ret_via_queue, args=(target, q))
            self.thread_handles.append((t, q))
            t.start()

    def join_all(self, raise_exceptions=True):
        if self.results:
            return self.results

        for t, q in self.thread_handles:
            t.join()

        self.results = [q.get() for _, q in self.thread_handles]
        if raise_exceptions:
            for result in self.results:
                if 'exception' in result:
                    exc_info = result['exception']
                    raise exc_info[1].with_traceback(exc_info[2])
        return [x.get('return', None) for x in self.results]


def invoke_in_parallel(func, *args_sequences):
    vt = VectorThread(func_vector(func, list(zip(*args_sequences))))
    vt.start_all()
    return vt.join_all()


def invoke_different_funcs_in_parallel(*funcs):
    vt = VectorThread(funcs)
    vt.start_all()
    return vt.join_all()


def read_nonblocking(file_descriptor):
    oldfl = fcntl.fcntl(file_descriptor.fileno(), fcntl.F_GETFL)
    try:
        fcntl.fcntl(
            file_descriptor.fileno(),
            fcntl.F_SETFL,
            oldfl | os.O_NONBLOCK,
        )
        return file_descriptor.read()
    finally:
        fcntl.fcntl(file_descriptor.fileno(), fcntl.F_SETFL, oldfl)
