#
# Copyright 2017 Red Hat, Inc.
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
import collections
import os
import time


DEFAULT_TIMEOUT = 120


class Timeout(Exception):

    @property
    def last_result(self):
        return self.args[0]

    def __str__(self):
        return "Last evaluated result: {}".format(self.args[0])


def sync(exec_func,
         exec_func_args,
         success_criteria=lambda result: True,
         error_criteria=lambda error: True,
         timeout=DEFAULT_TIMEOUT):
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
    :param timeout: int
    """
    end_time = _monothonic_time() + timeout

    if isinstance(exec_func_args, collections.Mapping):
        kwargs = exec_func_args
        args = ()
    else:
        args = exec_func_args
        kwargs = {}

    try:
        result = exec_func(*args, **kwargs)
    except Exception as e:
        if error_criteria(e):
            raise
        result = e
    else:
        if success_criteria(result):
            return

    while _monothonic_time() < end_time:
        time.sleep(3)
        try:
            result = exec_func(*args, **kwargs)
        except Exception as e:
            if error_criteria(e):
                raise
            result = e
        else:
            if success_criteria(result):
                return

    raise Timeout(result)


def _monothonic_time():
    return os.times()[4]
