#
# Copyright 2020-2021 Red Hat, Inc.
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

import contextlib

from ost_utils import assertions


@contextlib.contextmanager
def wait_for_event(engine, event_id, timeout=assertions.LONG_TIMEOUT):
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
            assertions.assert_true_within(
               lambda:
               any(e.code == e_id for e in events.list(from_=last_event)),
               timeout
            )


def get_jobs_statuses(engine, correlation_id):
    # Gets a list of jobs statuses by the specified correlation id.
    jobs = engine.jobs_service().list(
        search=f'correlation_id={correlation_id}'
    )
    return {job.status for job in jobs}
