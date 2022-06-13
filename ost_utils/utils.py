#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import fcntl
import functools
import logging
import os
import queue
import sys
import threading
import time

LOGGER = logging.getLogger(__name__)


class EggTimer:
    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *_):
        pass

    def elapsed(self):
        return (time.time() - self.start_time) > self.timeout


def _ret_via_queue(func, queue):
    try:
        queue.put({'return': func()})
    except Exception:
        LOGGER.debug(
            'Error while running thread %s',
            threading.current_thread().name,
            exc_info=True,
        )
        queue.put({'exception': sys.exc_info()})


def func_vector(target, args_sequence):
    return [functools.partial(target, *args) for args in args_sequence]


class VectorThread:
    def __init__(self, targets):
        self.targets = targets
        self.queues = [queue.Queue] * len(targets)
        self.thread_handles = []
        self.results = []

    def start_all(self):
        for target, q in zip(self.targets, self.queues):
            t = threading.Thread(target=_ret_via_queue, args=(target, q))
            self.thread_handles.append(t)
            t.start()

    def join_all(self, raise_exceptions=True):
        if self.results:
            return self.results

        for t in self.thread_handles:
            t.join()

        self.results = [q.get() for q in self.queues]
        exceptions = [result['exception'] for result in self.results if 'exception' in result]

        if exceptions:
            LOGGER.debug(f"{len(exceptions)} out of {len(self.targets)} threads raised exceptions:")
            for exc in exceptions:
                LOGGER.debug(f"{exc}")
            if raise_exceptions:
                exc_info = exceptions[0]
                raise exc_info[1].with_traceback(exc_info[2])

        return [result.get('return', None) for result in self.results]


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
