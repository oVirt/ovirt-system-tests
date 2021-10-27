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


def true_within_short(func, allowed_exceptions=None, error_message=None):
    return equals_within_short(func, True, allowed_exceptions, error_message)


def equals_within_short(
    func, expected_value, allowed_exceptions=None, error_message=None
):
    return EqualsWithin(
        func,
        expected_value,
        SHORT_TIMEOUT,
        allowed_exceptions,
        error_message,
    )


def true_within_long(func, allowed_exceptions=None, error_message=None):
    return equals_within_long(func, True, allowed_exceptions, error_message)


def equals_within_long(
    func, expected_value, allowed_exceptions=None, error_message=None
):
    return EqualsWithin(
        func,
        expected_value,
        LONG_TIMEOUT,
        allowed_exceptions,
        error_message,
    )


def true_within(func, timeout, allowed_exceptions=None, error_message=None):
    return EqualsWithin(
        func,
        True,
        timeout,
        allowed_exceptions,
        error_message,
    )


class EqualsWithin:
    def __init__(
        self,
        func,
        expected_value,
        timeout,
        allowed_exceptions=None,
        error_message=None,
        sleep_interval=3,
    ):
        self.expected_value = expected_value
        self.error_message = error_message
        self.success_message = (
            f'{func.__name__}() -> {self.expected_value} == '
            f'{self.expected_value}'
        )

        self.returned_value = '<no-result-obtained>'
        allowed_exceptions = allowed_exceptions or []
        with _EggTimer(timeout) as timer:
            while not timer.elapsed():
                try:
                    self.returned_value = func()
                    if self.returned_value == self.expected_value:
                        break
                except Exception as exc:
                    if any(isinstance(exc, cls) for cls in allowed_exceptions):
                        time.sleep(sleep_interval)
                        continue

                    LOGGER.exception(
                        'Unexpected exception in %s', func.__name__
                    )
                    raise

                time.sleep(sleep_interval)

        if self.error_message is None:
            self.error_message = (
                f'{func.__name__}() -> {self.returned_value} != '
                f'{self.expected_value} after {timeout} seconds'
            )

    def __bool__(self):
        return self.returned_value == self.expected_value

    def __repr__(self):
        return self.success_message if bool(self) else self.error_message


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
