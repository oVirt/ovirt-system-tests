#
# Copyright 2018-2021 Red Hat, Inc.
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
import http

import ovirtsdk4

from ovirtlib import eventlib
from ovirtlib import joblib


def sd_deactivation_error_not_due_to_busy(error):
    """
    :param error: the error raised by a storage domain deactivation request
    :return: true if the error is not a 'storage domain busy' error.
    """
    CANNOT_DEACTIVATE = 'Cannot deactivate'
    HAS_RUNNING_TASKS = 'while there are running tasks'
    RELATED_OP = 'Related operation is currently in progress'
    return not (
        isinstance(error, ovirtsdk4.Error) and
        CANNOT_DEACTIVATE in str(error) and
        (HAS_RUNNING_TASKS in str(error) or RELATED_OP in str(error))
    )


def sd_destroy_error_not_due_to_busy(error):
    """
    :param error: the error raised by a storage domain destroy request
    :return: true if the error is not a 'storage domain busy' error.
    """
    CANNOT_DESTROY = 'Cannot destroy'
    RELATED_OP = 'Related operation is currently in progress'
    TRY_AGAIN_LATER = 'Please try again later'
    return not (
        isinstance(error, ovirtsdk4.Error) and
        CANNOT_DESTROY in str(error) and
        RELATED_OP in str(error) and
        TRY_AGAIN_LATER in str(error)
    )


def is_not_ovirt_or_unlisted(error, error_list):
    return not (isinstance(error, ovirtsdk4.Error) and
                [err for err in error_list if err in str(error)])


def is_not_http_conflict(error):
    if not isinstance(error, ovirtsdk4.Error):
        return True
    return error.code != http.HTTPStatus.CONFLICT


def report_status(func):
    def inner(self, *args, **kwargs):
        events = eventlib.EngineEvents(self.system)
        description = _create_description('before', self)
        events.add(description=description)

        func(self, *args, **kwargs)
        description = _create_description('after', self)
        events.add(description=description)

    def _create_description(when, self):
        description = (f'OST - jobs: {self.__class__.__name__} '
                       f'{when} {func.__name__}, ')
        try:
            description += f'status: {self.status}, '
        except AttributeError:
            pass
        except ovirtsdk4.NotFoundError:
            description += 'entity not found, '
        description += (f'jobs: '
                        f'{joblib.AllJobs(self.system).describe_ill_fated()}')
        return description

    return inner
