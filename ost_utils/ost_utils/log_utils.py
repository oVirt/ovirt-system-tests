#
# Copyright 2015-2021 Red Hat, Inc.
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
"""
This module defines the special logging tools that lago uses
"""
import logging
import logging.config
import traceback
import uuid as uuid_m
from functools import wraps

#: Message template that will trigger a task
START_TASK_TRIGGER_MSG = 'start task%s'
#: Message template that will trigger a task end
END_TASK_TRIGGER_MSG = 'end task%s'


class LogTask:
    """
    Context manager for a log task

    Example:
        >>> with LogTask('mytask'):
        ...     pass
    """

    def __init__(
        self,
        task,
        logger=logging,
        level='info',
        propagate_fail=True,
        uuid=None,
    ):
        self.task = task
        self.logger = logger
        self.level = level
        self.propagate = propagate_fail
        if uuid is None:
            self.uuid = uuid_m.uuid4()
        self.header = self.task
        if self.level != 'info':
            self.header = ':{0}:{1}:'.format(str(self.uuid), self.task)


    def __enter__(self):
        getattr(self.logger, self.level)(START_TASK_TRIGGER_MSG % self.header)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and self.propagate:
            end_log_task(self.header, level='error')
            str_tb = ''.join(traceback.format_tb(exc_tb))
            self.logger.debug(str_tb)
            return False
        else:
            getattr(self.logger,
                    self.level)(END_TASK_TRIGGER_MSG % self.header)


def end_log_task(task, logger=logging, level='info'):
    """
    Ends a log task

    Args:
        task (str): name of the log task to end
        logger (logging.Logger): logger to use
        level (str): log level to use

    Returns:
        None
    """
    getattr(logger, level)(END_TASK_TRIGGER_MSG % task)
