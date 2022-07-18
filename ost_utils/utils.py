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
        self._start_time = None

    def __enter__(self):
        self._start_time = time.time()
        return self

    def __exit__(self, *_):
        pass

    @property
    def start_time(self):
        if self._start_time is None:
            raise RuntimeError("Timer not yet started")
        return self._start_time

    @property
    def running_time(self):
        return time.time() - self.start_time

    def elapsed(self):
        return self.running_time > self.timeout


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


class TimeoutException(Exception):
    pass


class VectorThread:
    def __init__(self, targets, daemon=False):
        self.targets = targets
        self.queues = [queue.Queue()] * len(targets)
        self.thread_handles = []
        self.results = []
        self.daemon = daemon

    def start_all(self):
        for target, q in zip(self.targets, self.queues):
            t = threading.Thread(target=_ret_via_queue, args=(target, q), daemon=self.daemon)
            self.thread_handles.append(t)
            t.start()

    def join_all(self, raise_exceptions=True, timeout=None):
        if self.results:
            return self.results

        self._join_threads(timeout)
        self._gather_results()
        self._handle_exceptions(raise_exceptions)

        return [result.get('return', None) for result in self.results]

    def _join_threads(self, timeout):
        timer = EggTimer(timeout)
        # never time out if timeout is None
        if timeout is None:
            timer.elapsed = lambda: False

        loop_timeout = timeout
        raise_timeout = False
        with timer:
            for t in self.thread_handles:
                t.join(timeout=loop_timeout)
                # if we've reached a timeout let's give the rest of the threads
                # a chance to join immediately
                if timer.elapsed():
                    LOGGER.debug("Reached timeout waiting on a thread. Trying to join remaining ones.")
                    loop_timeout = 0
                    raise_timeout = True
                else:
                    if loop_timeout is not None:
                        loop_timeout -= timer.running_time

        if raise_timeout:
            raise TimeoutException()

    def _gather_results(self):
        for q in self.queues:
            self.results.append(q.get(block=False))

    def _handle_exceptions(self, raise_exceptions):
        exceptions = [result['exception'] for result in self.results if 'exception' in result]

        if exceptions:
            LOGGER.debug(f"{len(exceptions)} out of {len(self.targets)} threads raised exceptions:")
            for exc in exceptions:
                LOGGER.debug(f"{exc}")
            if raise_exceptions:
                exc_info = exceptions[0]
                raise exc_info[1].with_traceback(exc_info[2])


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
