#
# Copyright 2021 Red Hat, Inc.
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
from ovirtsdk4.types import JobStatus

from ovirtlib import syncutil
from ovirtlib.sdkentity import SDKRootEntity


class EngineJobs(SDKRootEntity):

    def __init__(self, parent_sdk_system, job_description_predicate):
        super(EngineJobs, self).__init__(parent_sdk_system)
        self._job_description_predicate = job_description_predicate

    def _get_parent_service(self, system):
        return system.jobs_service

    def list(self):
        return [
            job for job in self._parent_service.list()
            if self._job_description_predicate(job.description)
            and 'Adding an External Event' not in job.description
        ]

    def describe_started(self):
        started = self._list_for_status((JobStatus.STARTED,))
        return [job.description for job in started]

    def describe_ill_fated(self):
        ill_fated = self._list_for_status(
            (JobStatus.ABORTED, JobStatus.UNKNOWN, JobStatus.FAILED)
        )
        return [f'{job.description}:{job.status}' for job in ill_fated]

    def done(self):
        return not self._list_for_status(
            (JobStatus.STARTED, JobStatus.UNKNOWN)
        )

    def wait_for_done(self):
        syncutil.sync(
            exec_func=lambda: self.done,
            exec_func_args=(),
            success_criteria=lambda done: done
        )

    def _list_for_status(self, job_statuses):
        return [job for job in self.list() if job.status in job_statuses]


class AllJobs(EngineJobs):

    def __init__(self, parent_sdk_system):
        super(AllJobs, self).__init__(parent_sdk_system, lambda d: True)


class ActivateHostJobs(EngineJobs):

    def __init__(self, parent_sdk_system):
        super(ActivateHostJobs, self).__init__(
            parent_sdk_system,
            lambda description: 'Activating Host' in description
        )


class RemoveVmJobs(EngineJobs):

    def __init__(self, parent_sdk_system):
        super(RemoveVmJobs, self).__init__(
            parent_sdk_system, lambda description: 'Removing VM' in description
        )


class LaunchVmJobs(EngineJobs):

    def __init__(self, parent_sdk_system):
        super(LaunchVmJobs, self).__init__(
            parent_sdk_system,
            lambda description: 'Launching VM' in description
        )
