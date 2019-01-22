#
# Copyright 2014-2017 Red Hat, Inc.
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
import functools
import pkg_resources
import sys


def get_data_file(basename):
    """
    Load a data as a string from the data directory

    Args:
        basename(str): filename

    Returns:
        str: string representation of the file
    """
    return pkg_resources.resource_string(
        __name__, '/'.join(['data', basename])
    )


def available_sdks(modules=None):
    modules = modules or sys.modules
    res = []
    if 'ovirtsdk' in modules:
        res.append('3')
    if 'ovirtsdk4' in modules:
        res.append('4')
    return res


def require_sdk(version, modules=None):
    modules = modules or sys.modules

    def wrap(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            sdks = available_sdks(modules)
            if version not in sdks:
                raise RuntimeError(
                    (
                        '{0} requires oVirt Python SDK v{1}, '
                        'available SDKs: {2}'
                    ).format(func.__name__, version, ','.join(sdks))
                )
            else:
                return func(*args, **kwargs)

        return wrapped_func

    return wrap


def partial(func, *args, **kwargs):
    partial_func = functools.partial(func, *args, **kwargs)
    functools.update_wrapper(partial_func, func)
    return partial_func
