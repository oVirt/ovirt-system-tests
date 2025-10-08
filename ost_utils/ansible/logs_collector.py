#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import json
import os
import shutil

from ost_utils.ansible import private_dir as pd


class LogsCollector:
    """Handles saving ansible logs from all ansible_runner executions"""

    @classmethod
    def save(cls, target_dir):
        logs_path = os.path.join(target_dir, "ansible_logs")
        raw_logs_path = os.path.join(logs_path, "raw")
        os.makedirs(raw_logs_path, exist_ok=True)

        cls._save_raw_events(pd.PrivateDir.event_data_files(), raw_logs_path)

        cls._save_events_stdouts(pd.PrivateDir.event_data_files(), logs_path)

    @classmethod
    def _save_raw_events(cls, event_data_files, target_dir):
        for event_file in event_data_files:
            shutil.copy(event_file, target_dir)

    @classmethod
    def _save_events_stdouts(cls, event_data_files, target_dir):
        all_events = cls._load_events(event_data_files)

        for host, events in all_events.items():
            log_path = os.path.join(target_dir, host)
            with open(log_path, 'w', encoding='utf-8') as log_file:
                for event in sorted(events, key=lambda e: e['created']):
                    log_file.write(event['stdout'])
                    log_file.write('\n')

    @classmethod
    def _load_events(cls, event_data_files):
        events = {}

        for path in event_data_files:
            with open(path, encoding='utf-8') as event_file:
                event = json.load(event_file)
                if cls._should_include_event(event):
                    host = event['event_data']['host']
                    events.setdefault(host, []).append(event)

        return events

    @classmethod
    def _should_include_event(cls, event):
        # no stdout - nothing to log
        if len(event.get('stdout', '')) == 0:
            return False

        # if we can't sort an event by its creation time
        # we can't log it in an understandable way
        if event.get('created', None) is None:
            return False

        # logs are grouped by host, so we need this information
        if event.get('event_data', {}).get('host', None) is None:
            return False

        return True
