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
import datetime
import functools
import logging
import os
import time
import unittest.case
import nose.plugins
from nose.plugins.skip import SkipTest
import utils


from ost_utils.vm import VagrantHosts

LOGGER = logging.getLogger(__name__)
SHORT_TIMEOUT = 3 * 60
LONG_TIMEOUT = 10 * 60

_test_prefix = None


def get_test_prefix():
    global _test_prefix
    if _test_prefix is None:
        _test_prefix = os.environ.get('VAGRANT_CWD', os.curdir)
    return _test_prefix


def get_prefixed_name(entity_name):
    suite = os.environ.get('SUITE')
    return (
        os.path.basename(suite).replace('.', '-') + '-' + entity_name
    )


def with_ovirt_prefix(func):
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        prefix = VagrantHosts()
        return func(prefix, *args, **kwargs)
    return wrapper


def with_ovirt_api(func):
    @functools.wraps(func)
    @with_ovirt_prefix
    def wrapper(prefix, *args, **kwargs):
        return func(prefix.virt_env.engine_vm().get_api(), *args, **kwargs)

    return wrapper


def with_ovirt_api4(func):
    @functools.wraps(func)
    @with_ovirt_prefix
    def wrapper(prefix, *args, **kwargs):
        return func(
            prefix.virt_env.engine_vm().get_api(api_ver=4), *args, **kwargs
        )

    return wrapper


def with_ovirt_api4_service(func):
    @functools.wraps(func)
    @with_ovirt_prefix
    def wrapper(prefix, *args, **kwargs):
        return func(
            prefix.virt_env.engine_vm().get_api_v4_system_service(), *args,
            **kwargs
        )

    return wrapper


def test_sequence_gen(test_list):
    for test in test_list:

        def wrapped_test():
            test()

        setattr(wrapped_test, 'description', test.__name__)
        yield wrapped_test


class LogCollectorPlugin(nose.plugins.Plugin):
    name = 'log-collector-plugin'

    def __init__(self, prefix):
        nose.plugins.Plugin.__init__(self)
        self._prefix = prefix

    def options(self, parser, env=None):
        env = env if env is not None else os.environ
        super(LogCollectorPlugin, self).options(parser, env)

    def configure(self, options, conf):
        super(LogCollectorPlugin, self).configure(options, conf)

    def addError(self, test, err):
        self._addFault(test, err)

    def addFailure(self, test, err):
        self._addFault(test, err)

    def _addFault(self, test, err):
        suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        test_name = '%s-%s' % (test.id(), suffix)

        try:
            self._prefix.collect_artifacts(
                self._prefix.paths.test_logs(test_name), False
            )
        except (ExtractPathError, ExtractPathNoPathError) as e:
            LOGGER.debug(e, exc_info=True)



def _instance_of_any(obj, cls_list):
    return any(True for cls in cls_list if isinstance(obj, cls))


def assert_equals_within(
    func, value, timeout, allowed_exceptions=None, initial_wait=10
):
    allowed_exceptions = allowed_exceptions or []
    with utils.EggTimer(timeout) as timer:
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
        raise AssertionError(
            '%s != %s after %s seconds' % (res, value, timeout)
        )
    # if func repeatedly raises any of the allowed exceptions, res remains
    # unbound throughout the function, resulting in an UnboundLocalError.
    except UnboundLocalError:
        raise AssertionError(
            '%s failed to evaluate after %s seconds' %
            (func.__name__, timeout)
        )


def assert_equals_within_short(func, value, allowed_exceptions=None):
    allowed_exceptions = allowed_exceptions or []
    assert_equals_within(
        func, value, SHORT_TIMEOUT, allowed_exceptions=allowed_exceptions
    )


def assert_equals_within_long(func, value, allowed_exceptions=None):
    allowed_exceptions = allowed_exceptions or []
    assert_equals_within(
        func, value, LONG_TIMEOUT, allowed_exceptions=allowed_exceptions
    )


def assert_true_within(func, timeout, allowed_exceptions=None):
    assert_equals_within(func, True, timeout, allowed_exceptions)


def assert_true_within_short(func, allowed_exceptions=None):
    assert_equals_within_short(func, True, allowed_exceptions)


def assert_true_within_long(func, allowed_exceptions=None):
    assert_equals_within_long(func, True, allowed_exceptions)

def main():
    print "testlib"



if __name__ == "__main__":
    main()
