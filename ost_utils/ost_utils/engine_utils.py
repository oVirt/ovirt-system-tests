#
# Copyright 2020 Red Hat, Inc.
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

from __future__ import absolute_import

import contextlib

from ost_utils import assertions


@contextlib.contextmanager
def wait_for_event(engine, event_id):
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
            assertions.assert_true_within_long(
               lambda:
               any(e.code == e_id for e in events.list(from_=last_event))
            )
