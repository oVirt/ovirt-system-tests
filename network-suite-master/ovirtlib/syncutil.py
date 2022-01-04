#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import collections
import logging
import os
import time

from ovirtlib import eventlib

DEFAULT_DELAY_START = 0
DEFAULT_INTERVAL = 3
DEFAULT_TIMEOUT = 120
DELIM = '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'


class Timeout(Exception):
    @property
    def last_result(self):
        return self.args[0]

    def __str__(self):
        return "Last evaluated result: {}".format(self.args[0])


def sync(
    exec_func,
    exec_func_args,
    success_criteria=lambda result: True,
    error_criteria=lambda error: True,
    delay_start=DEFAULT_DELAY_START,
    retry_interval=DEFAULT_INTERVAL,
    timeout=DEFAULT_TIMEOUT,
    sdk_entity=None,
):
    """Sync an operation until it either:

    - succeeds (according to the success_criteria specified)
    - fails due to timing out (after the specified timeout)
    - fails due to a terminal error (according to the error_criteria specified)

    A caller may specifiy a success_criteria function that should return:

    - False if the sync should continue to retry
    - True if the sync should terminate immediately

    A caller may also specify an error_criteria function if the sync
    should continue to retry when the operation fails with an anticipated
    exception. This function will be called back with the exception and
    should return:

    - False if the sync should continue to retry
    - True if the sync should stop and the exception raised back to the caller

    By default, both success_criteria and error_criteria return True, causing
    all results and all errors to return and raise respectively. The default
    timeout is 120 seconds.

    :param exec_func: callable
    :param exec_func_args: tuple/dict
    :param success_criteria: callable
    :param error_criteria: callable
    :param delay_start: time to wait before first call to exec_func
    :param retry_interval: time between retries of exec_func
    :param timeout: int
    :param sdk_entity: ovirtlib instance for which auditing to engine.log
                       before each retry is desired
    :return: the result of running the exec_func
    """
    end_time = _monothonic_time() + timeout

    args, kwargs = _parse_args(exec_func_args)
    logger = SyncLogger(exec_func, args, kwargs)
    logger.log_start()
    try:
        time.sleep(delay_start)
        _audit(exec_func, sdk_entity, 0)
        result = exec_func(*args, **kwargs)
        logger.log_iteration(0, result)
    except Exception as e:
        logger.log_iteration(0, e)
        if error_criteria(e):
            logger.log_end()
            raise
        result = e
    else:
        if success_criteria(result):
            logger.log_end()
            return result

    i = 0
    while _monothonic_time() < end_time:
        i += 1
        time.sleep(retry_interval)
        try:
            _audit(exec_func, sdk_entity, i)
            result = exec_func(*args, **kwargs)
            logger.log_iteration(i, result)
        except Exception as e:
            logger.log_iteration(i, e)
            if success_criteria(e):
                logger.log_end()
                return e
            if error_criteria(e):
                logger.log_end()
                raise
            result = e
        else:
            if success_criteria(result):
                logger.log_end()
                return result

    logger.log_end()
    raise Timeout(result)


def _audit(exec_func, sdk_entity, i):
    if sdk_entity:
        try:
            repr = sdk_entity.__repr__()
        except Exception:
            repr = f'{sdk_entity.__class__.__name__}.__repr__() call failed'
        eventlib.EngineEvents(sdk_entity.system).add(
            f'{DELIM} OST - retry[{i}] {exec_func.__name__}: {repr}'
        )


def re_run(exec_func, exec_func_args, count, interval):
    args, kwargs = _parse_args(exec_func_args)
    results = []
    for _ in range(count):
        try:
            r = exec_func(*args, **kwargs)
        except Exception as e:
            r = e
        results.append(r)
        time.sleep(interval)
    return results


def _parse_args(exec_func_args):
    if isinstance(exec_func_args, collections.abc.Mapping):
        kwargs = exec_func_args
        args = ()
    else:
        args = exec_func_args
        kwargs = {}
    return args, kwargs


def _monothonic_time():
    return os.times()[4]


class SyncLogger:
    def __init__(self, exec_func, args, kwargs):
        self._func = exec_func
        self._args = args
        self._kwargs = kwargs
        self._logger = logging.getLogger(__name__)

    def log_start(self):
        self._debug('start')

    def log_end(self):
        self._debug('end')

    def log_iteration(self, iteration, output):
        self._debug(f'iteration {iteration} output: {output}')

    def _debug(self, phase):
        self._logger.debug(
            f'sync {phase} for: {self._func}, {self._args}, {self._kwargs}'
        )
