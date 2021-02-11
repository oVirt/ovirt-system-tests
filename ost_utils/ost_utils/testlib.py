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

# TODO: remove once code is aligned to new location
from ost_utils.assertions import SHORT_TIMEOUT
from ost_utils.assertions import LONG_TIMEOUT
from ost_utils.assertions import assert_equals_within
from ost_utils.assertions import assert_equals_within_short
from ost_utils.assertions import assert_equals_within_long
from ost_utils.assertions import assert_true_within
from ost_utils.assertions import assert_true_within_short
from ost_utils.assertions import assert_true_within_long

from ost_utils.vm import VagrantHosts

LOGGER = logging.getLogger(__name__)

_test_prefix = None


def get_test_prefix():
    global _test_prefix
    if _test_prefix is None:
        _test_prefix = os.environ.get('VAGRANT_CWD', os.curdir)
    return _test_prefix


def get_prefixed_name(entity_name):
    suite = os.environ.get('SUITE')
    return (
        os.path.basename(suite).replace('.', '-').replace('-','_') + '-' + entity_name
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


def main():
    print("testlib")



if __name__ == "__main__":
    main()
