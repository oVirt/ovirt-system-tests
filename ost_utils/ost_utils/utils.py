#
# Copyright 2014 Red Hat, Inc.
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

import collections
import datetime
import fcntl
import functools
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import textwrap
import time
import yaml
import pkg_resources
from io import StringIO
import argparse
import configparser
import uuid as uuid_m
import hashlib

import six

from six.moves import queue

from ost_utils.log_utils import LogTask, setup_prefix_logging

LOGGER = logging.getLogger(__name__)

class OSTUserException(Exception):
    """
    Exception to throw when a timeout is reached
    """
    pass

class TimerException(Exception):
    """
    Exception to throw when a timeout is reached
    """
    pass


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
                    six.reraise(*exc_info)
        return [x.get('return', None) for x in self.results]


def invoke_in_parallel(func, *args_sequences):
    vt = VectorThread(func_vector(func, list(zip(*args_sequences))))
    vt.start_all()
    return vt.join_all()


def invoke_different_funcs_in_parallel(*funcs):
    vt = VectorThread(funcs)
    vt.start_all()
    return vt.join_all()


def service_is_enabled(name):
    ret, out, _ = run_command(['systemctl', 'is-enabled', name])
    if ret == 0 and out.strip() == 'enabled':
        return True
    return False


# Copied from VDSM: lib/vdsm/utils.py
class RollbackContext(object):
    '''
    A context manager for recording and playing rollback.
    The first exception will be remembered and re-raised after rollback

    Sample usage:
    > with RollbackContext() as rollback:
    >     step1()
    >     rollback.prependDefer(lambda: undo step1)
    >     def undoStep2(arg): pass
    >     step2()
    >     rollback.prependDefer(undoStep2, arg)

    More examples see tests/utilsTests.py @ vdsm code
    '''

    def __init__(self, *args):
        self._finally = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        If this function doesn't return True (or raises a different
        exception), python re-raises the original exception once this
        function is finished.
        """
        undoExcInfo = None
        for undo, args, kwargs in self._finally:
            try:
                undo(*args, **kwargs)
            except Exception:
                # keep the earliest exception info
                if undoExcInfo is None:
                    undoExcInfo = sys.exc_info()

        if exc_type is None and undoExcInfo is not None:
            six.reraise(undoExcInfo[0], undoExcInfo[1], undoExcInfo[2])

    def defer(self, func, *args, **kwargs):
        self._finally.append((func, args, kwargs))

    def prependDefer(self, func, *args, **kwargs):
        self._finally.insert(0, (func, args, kwargs))

    def clear(self):
        self._finally = []


class ExceptionTimer(object):
    def __init__(self, timeout):
        self.timeout = timeout or 0

    def __enter__(self):
        self.start()

    def __exit__(self, *_):
        self.stop()

    def start(self):
        def raise_timeout(*_):
            raise TimerException('Passed %d seconds' % self.timeout)

        signal.signal(signal.SIGALRM, raise_timeout)
        signal.alarm(self.timeout)

    def stop(self):
        signal.alarm(0)


class Flock(object):
    """A wrapper class around flock

    Attributes:
        path(str): Path to the lock file
        readonly(bool): If true create a shared lock, otherwise
            create an exclusive lock.
        blocking(bool) If true block the calling process if the
            lock is already acquired.
    """

    def __init__(self, path, readonly=False, blocking=True):
        self._path = path
        self._fd = None
        if readonly:
            self._op = fcntl.LOCK_SH
        else:
            self._op = fcntl.LOCK_EX

        if not blocking:
            self._op |= fcntl.LOCK_NB

    def acquire(self):
        """Acquire the lock

        Raises:
            IOError: if the call to flock fails
        """
        self._fd = open(self._path, mode='w+')
        fcntl.flock(self._fd, self._op)

    def release(self):
        self._fd.close()


class LockFile(object):
    """
    Context manager that creates a file based lock, with optional
    timeout in the acquire operation.

    This context manager should be used only from the main Thread.

    Args:
        path(str): path to the dir to lock
        timeout(int): timeout in seconds to wait while acquiring the lock
        lock_cls(callable): A callable which returns a Lock object that
            implements the acquire and release methods.
            The default is Flock.
        **kwargs(dict): Any other param to pass to the `lock_cls` instance.

    """

    def __init__(self, path, timeout=None, lock_cls=None, **kwargs):
        self.path = path
        self.timeout = timeout or 0
        self._lock_cls = lock_cls or Flock
        self.lock = self._lock_cls(path=path, **kwargs)

    def __enter__(self):
        """
        Start the lock with timeout if needed in the acquire operation

        Raises:
            TimerException: if the timeout is reached before acquiring the lock
        """
        try:
            with ExceptionTimer(timeout=self.timeout):
                LOGGER.debug('Acquiring lock for {}'.format(self.path))
                self.lock.acquire()
                LOGGER.debug('Holding the lock for {}'.format(self.path))
        except TimerException:
            raise TimerException(
                'Unable to acquire lock for %s in %s secs',
                self.path,
                self.timeout,
            )

    def __exit__(self, *_):
        LOGGER.debug('Trying to release lock for {}'.format(self.path))
        self.lock.release()
        LOGGER.debug('Lock for {} was released'.format(self.path))


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


def json_dump(obj, f):
    return json.dump(obj, f, indent=4)


def deepcopy(original_obj):
    """
    Creates a deep copy of an object with no crossed referenced lists or dicts,
    useful when loading from yaml as anchors generate those cross-referenced
    dicts and lists

    Args:
        original_obj(object): Object to deep copy

    Return:
        object: deep copy of the object
    """
    if isinstance(original_obj, list):
        return list(deepcopy(item) for item in original_obj)
    elif isinstance(original_obj, dict):
        return dict((key, deepcopy(val)) for key, val in original_obj.items())
    else:
        return original_obj


def load_virt_stream(virt_fd):
    """
    Loads the given conf stream into a dict, trying different formats if
    needed

    Args:
        virt_fd (str): file like objcect with the virt config to load

    Returns:
        dict: Loaded virt config
    """
    try:
        virt_conf = json.load(virt_fd)
    except ValueError:
        virt_fd.seek(0)
        virt_conf = yaml.load(virt_fd)

    return deepcopy(virt_conf)


def add_timestamp_suffix(base_string):
    return datetime.datetime.fromtimestamp(
        time.time()
    ).strftime(base_string + '.%Y-%m-%d_%H:%M:%S')


def rotate_dir(base_dir):
    shutil.move(base_dir, add_timestamp_suffix(base_dir))


def ipv4_to_mac(ip):
    # Mac addrs of domains are 54:52:xx:xx:xx:xx where the last 4 octets are
    # the hex repr of the IP address)
    mac_addr_pieces = [0x54, 0x52] + [int(y) for y in ip.split('.')]
    return ':'.join([('%02x' % x) for x in mac_addr_pieces])

def _add_subparser_to_cp(cp, section, actions, incl_unset):
    cp.add_section(section)
    print_actions = (
        action for action in actions
        if (action.default and action.default != '==SUPPRESS==') or
        (action.default is None and incl_unset)
    )
    for action in print_actions:
        var = str(action.dest)
        if action.default is None:
            var = '#{0}'.format(var)
        if action.help:
            for line in textwrap.wrap(action.help, width=70):
                cp.set(section, '# {0}'.format(line))
        cp.set(section, var, str(action.default))
    if len(cp.items(section)) == 0:
        cp.remove_section(section)
