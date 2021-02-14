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

import logging
import time

logger = logging.getLogger(__name__)


def exponential_retrier(
        attempts=5, base_coefficient=10, max_iteration_sleeptime=300,
        base=2, sleep_at_first_attempt=False):

    """
    A generator function that sleeps between retries. Each iteration we sleep
    for base_coefficient * base ** n seconds (n is attempts) for the maximum
    of max_iteration_sleeptime.
    Use in a gradual way longer waits between retries for consecutive error
    responses.

    Args:
        attempts (int): maximum number of times to try; defaults to 5.
        base_coefficient (float): how many seconds to sleep between tries
            on the first iteration; defaults to 10 seconds.
        max_iteration_sleeptime (float): maximum number of seconds to sleep for
            any iteration; defaults to 300 seconds (five minutes).
        base (float): number to multiply the base_coefficient with.
            Exponentially grows with each attempt; defaults to 2.
        sleep_at_first_attempt (boolean): Do we want to sleep at first attempt;
            defaults to False
    """
    attempt_num = 0
    if not sleep_at_first_attempt:
        yield 0
        attempt_num += 1
    for attempt_num in range(attempt_num, attempts):
        actual_sleeptime = min(
            base_coefficient * base ** attempt_num,
            max_iteration_sleeptime)
        logger.debug(
            "attempt {}/{}, {} seconds sleeping".
            format(attempt_num + 1, attempts, actual_sleeptime))
        time.sleep(actual_sleeptime)
        yield actual_sleeptime


def linear_retrier(
        attempts=5, iteration_sleeptime=10, sleep_at_first_attempt=False):

    """
    A generator function that sleeps between retries
    Each iteration we sleep for iteration_sleeptime after each iteration.

    Args:
        attempts (int): maximum number of times to try; defaults to 5
        iteration_sleeptime (float): how many seconds to sleep between tries;
            defaults to 10 seconds
        sleep_at_first_attempt (boolean): Do we want to sleep at first attempt;
            defaults to False
    """
    return exponential_retrier(
        attempts, iteration_sleeptime,
        max_iteration_sleeptime=iteration_sleeptime, base=1,
        sleep_at_first_attempt=False)


def main():
    logger.debug("linear")
    for sleep_time in linear_retrier(attempts=5, iteration_sleeptime=1):
        logger.debug(sleep_time)
    logger.debug("exponential")
    for sleep_time in exponential_retrier(
            attempts=5, base_coefficient=1, max_iteration_sleeptime=200):
        logger.debug(sleep_time)


if __name__ == "__main__":
    main()
