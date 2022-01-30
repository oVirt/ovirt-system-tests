#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from ovirtsdk4.types import JobStatus

from . import eventlib
from . import syncutil
from .sdkentity import SDKRootEntity


class EngineJobs(SDKRootEntity):
    def __init__(self, parent_sdk_system, job_description_predicate):
        super(EngineJobs, self).__init__(parent_sdk_system)
        self._job_description_predicate = job_description_predicate

    def _get_parent_service(self, system):
        return system.jobs_service

    def list(self):
        return [
            job
            for job in self._parent_service.list()
            if self._job_description_predicate(job.description) and 'Adding an External Event' not in job.description
        ]

    def describe_started(self):
        started = self._list_for_status((JobStatus.STARTED,))
        return [job.description for job in started]

    def describe_ill_fated(self):
        ill_fated = self._list_for_status((JobStatus.ABORTED, JobStatus.UNKNOWN, JobStatus.FAILED))
        return [f'{job.description}:{job.status}' for job in ill_fated]

    def done(self):
        return not self._list_for_status((JobStatus.STARTED, JobStatus.UNKNOWN))

    def wait_for_done(self):
        self._report_started()
        # there is a small window for TOCTTOU error here
        if not self.done():
            syncutil.sync(
                exec_func=lambda: self.done,
                exec_func_args=(),
                success_criteria=lambda done: done,
            )
            self._report_started()
            self._report_ill_fated()

    def _report_started(self):
        eventlib.EngineEvents(self.system).add(
            f'OST - jobs: on wait for done - started jobs: ' f'{self.describe_started()} '
        )

    def _report_ill_fated(self):
        eventlib.EngineEvents(self.system).add(f'OST - jobs: on wait for done:' f'{self.describe_ill_fated()}')

    def _list_for_status(self, job_statuses):
        return [job for job in self.list() if job.status in job_statuses]


class AllJobs(EngineJobs):
    def __init__(self, parent_sdk_system):
        super(AllJobs, self).__init__(parent_sdk_system, lambda d: True)


class ActivateHostJobs(EngineJobs):
    def __init__(self, parent_sdk_system):
        super(ActivateHostJobs, self).__init__(
            parent_sdk_system,
            lambda description: 'Activating Host' in description,
        )


class RemoveVmJobs(EngineJobs):
    def __init__(self, parent_sdk_system):
        super(RemoveVmJobs, self).__init__(parent_sdk_system, lambda description: 'Removing VM' in description)


class LaunchVmJobs(EngineJobs):
    def __init__(self, parent_sdk_system):
        super(LaunchVmJobs, self).__init__(
            parent_sdk_system,
            lambda description: 'Launching VM' in description,
        )
