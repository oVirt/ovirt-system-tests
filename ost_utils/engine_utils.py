#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import contextlib

from ost_utils import assert_utils


@contextlib.contextmanager
def wait_for_event(engine, event_id, timeout=assert_utils.LONG_TIMEOUT):
    '''
    event_id could either be an int - a single
    event ID or a list - multiple event IDs
    that all will be checked
    '''
    events = engine.events_service()
    last_event = int(events.list(max=2)[0].id)
    try:
        yield
    finally:
        if isinstance(event_id, int):
            event_id = [event_id]
        for e_id in event_id:
            assert assert_utils.true_within(
                lambda: any(
                    e.code == e_id for e in events.list(from_=last_event)
                ),
                timeout,
            )


def get_jobs_statuses(engine, correlation_id):
    # Gets a list of jobs statuses by the specified correlation id.
    jobs = engine.jobs_service().list(
        search=f'correlation_id={correlation_id}'
    )
    return {job.status for job in jobs}
