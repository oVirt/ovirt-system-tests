#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import datetime

import logging

LOGGER = logging.getLogger('')


RUNNING_TIMES = {}


def pytest_runtest_logstart(nodeid, location):
    now = datetime.datetime.now()
    RUNNING_TIMES[location] = now
    print(now.strftime('started at %Y-%m-%d %H:%M:%S'), end=' ')
    LOGGER.debug(f'Running test: {nodeid}')


def pytest_runtest_logfinish(nodeid, location):
    now = datetime.datetime.now()
    then = RUNNING_TIMES[location]
    delta = int((now - then).total_seconds())
    print(" ({}s)".format(delta), end='')
    LOGGER.debug(f'Finished test: {nodeid} ({delta}s)')
