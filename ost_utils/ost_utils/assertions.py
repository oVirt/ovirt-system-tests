#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging
import time


LOGGER = logging.getLogger(__name__)

SHORT_TIMEOUT = 3 * 60
LONG_TIMEOUT = 10 * 60


def assert_equals_within(
    func,
    value,
    timeout,
    allowed_exceptions=None,
    initial_wait=10,
    error_message=None,
):
    allowed_exceptions = allowed_exceptions or []
    res = '<no-result-obtained>'
    with _EggTimer(timeout) as timer:
        while not timer.elapsed():
            try:
                res = func()
                if res == value:
                    return
            except Exception as exc:
                if _instance_of_any(exc, allowed_exceptions):
                    time.sleep(3)
                    continue

                LOGGER.exception("Unhandled exception in %s", func)
                raise

            if initial_wait == 0:
                time.sleep(3)
            else:
                time.sleep(initial_wait)
                initial_wait = 0
    try:
        if error_message is None:
            error_message = '%s != %s after %s seconds' % (res, value, timeout)
        raise AssertionError(error_message)
    # if func repeatedly raises any of the allowed exceptions, res remains
    # unbound throughout the function, resulting in an UnboundLocalError.
    except UnboundLocalError:
        raise AssertionError(
            '%s failed to evaluate after %s seconds' % (func.__name__, timeout)
        )


def assert_equals_within_short(
    func, value, allowed_exceptions=None, error_message=None
):
    allowed_exceptions = allowed_exceptions or []
    assert_equals_within(
        func,
        value,
        SHORT_TIMEOUT,
        allowed_exceptions=allowed_exceptions,
        error_message=error_message,
    )


def assert_equals_within_long(func, value, allowed_exceptions=None):
    allowed_exceptions = allowed_exceptions or []
    assert_equals_within(
        func, value, LONG_TIMEOUT, allowed_exceptions=allowed_exceptions
    )


def assert_true_within(func, timeout, allowed_exceptions=None):
    assert_equals_within(func, True, timeout, allowed_exceptions)


def assert_true_within_short(
    func, allowed_exceptions=None, error_message=None
):
    assert_equals_within_short(
        func, True, allowed_exceptions, error_message=error_message
    )


def assert_true_within_long(func, allowed_exceptions=None):
    assert_equals_within_long(func, True, allowed_exceptions)


def _instance_of_any(obj, cls_list):
    return any(True for cls in cls_list if isinstance(obj, cls))


class _EggTimer:
    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *_):
        pass

    def elapsed(self):
        return (time.time() - self.start_time) > self.timeout
