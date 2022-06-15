#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import ovirtsdk4

from . import eventlib
from . import joblib

DELIM = '--------------------------------------'


def sd_deactivation_error_not_due_to_busy(error):
    """
    :param error: the error raised by a storage domain deactivation request
    :return: true if the error is not a 'storage domain busy' error.
    """
    CANNOT_DEACTIVATE = 'Cannot deactivate'
    HAS_RUNNING_TASKS = 'while there are running tasks'
    RELATED_OP = 'Related operation is currently in progress'
    return not (
        isinstance(error, ovirtsdk4.Error)
        and CANNOT_DEACTIVATE in str(error)
        and (HAS_RUNNING_TASKS in str(error) or RELATED_OP in str(error))
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
        isinstance(error, ovirtsdk4.Error)
        and CANNOT_DESTROY in str(error)
        and RELATED_OP in str(error)
        and TRY_AGAIN_LATER in str(error)
    )


def is_not_ovirt_or_unlisted(error, error_list):
    return not (isinstance(error, ovirtsdk4.Error) and [err for err in error_list if err in str(error)])


def report_status(func):
    def inner(self, *args, **kwargs):
        events = eventlib.EngineEvents(self.system)
        description = _create_description('before', self)
        events.add(description=description)

        func(self, *args, **kwargs)
        description = _create_description('after', self)
        events.add(description=description)

    def _create_description(when, self):
        description = f'{DELIM} OST - {when}: ' f'{self.__class__.__name__} {func.__name__}, '
        try:
            description += f'status: {self.status}, '
        except AttributeError:
            pass
        except ovirtsdk4.NotFoundError:
            description += 'entity not found, '
        description += f'jobs: ' f'{joblib.AllJobs(self.system).describe_ill_fated()}'
        return description

    return inner
