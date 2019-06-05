#
# Copyright 2014, 2018 Red Hat, Inc.
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

import json
import nose.tools as nt
from ovirtlago import testlib

import logging
import time

host_state = 8
index_value = 1
wait_value = 300


def _wait_for_engine_migration(host, he_index, health, state):
    logging.info("Waiting for engine to migrate...")

    testlib.assert_true_within_long(lambda: _get_he_status(host)
        [he_index]["engine-status"]["health"] == health)

    testlib.assert_true_within_long(
        lambda: _check_migration_state(host, state) is False
    )
    logging.info("Engine has migrated.")

    logging.info("Waiting For System Stability...")
    time.sleep(wait_value)


def _is_state_maintenance(host, state):
    return_value = False
    status = _get_he_status(host)

    for k, v in status.items():
        if not k.isdigit():
            continue

        host_extra = v['extra'].split("\n")
        he_state = host_extra[host_state].split("=")[index_value]
        if he_state == "ReinitializeFSM" or he_state == state:
            return_value = True
            break

    return return_value


def _wait_for_engine_maintenance(host, he_index, value):
    logging.info("Waiting for Engine Maintenance to reset...")
    time.sleep(2)

    testlib.assert_true_within_long(lambda: _get_he_status(host)
        [he_index]["maintenance"] is value)

    testlib.assert_true_within_long(
        lambda: _is_state_maintenance(host, "LocalMaintenance") is False
    )

    logging.info("Engine Maintenance is reset.")


def _find_host_running_he_vm(hosts):
    status = _get_he_status(hosts[0])
    running_on = ""
    for k, v in status.items():
        if not k.isdigit():
            continue
        if v["engine-status"]["vm"] == "up":
            running_on = v["hostname"].split(".", 1)[0]
            break
    return k, next(h for h in hosts if h.name() == running_on)


def _get_he_status(host):
    ret = host.ssh(["hosted-engine", "--vm-status", "--json"])
    nt.assert_equals(ret.code, 0)

    try:
        return json.loads(ret.out)
    except ValueError:
        raise RuntimeError('could not parse JSON: %s' % ret.out)


def _check_migration_state(host, state):
    return_value = False
    status = _get_he_status(host)
    for k, v in status.items():
        if not k.isdigit():
            continue
        if v["engine-status"]["detail"] == state:
            return_value = True

    return return_value


@testlib.with_ovirt_prefix
def local_maintenance(prefix):
    logging.info("Waiting For System Stability...")
    time.sleep(wait_value)

    hosts = prefix.virt_env.host_vms()
    he_index, host = _find_host_running_he_vm(hosts)

    ret = host.ssh([
        "hosted-engine", "--set-maintenance", "--mode=local"])
    nt.assert_equals(ret.code, 0)

    _wait_for_engine_migration(host, he_index, "bad", "Migration Destination")

    ret = host.ssh(["hosted-engine", "--set-maintenance", "--mode=none"])
    nt.assert_equals(ret.code, 0)

    _wait_for_engine_maintenance(host, he_index, False)

    current_he_index, host = _find_host_running_he_vm(hosts)

    testlib.assert_true_within_short(
        lambda: he_index != current_he_index
    )


_TEST_LIST = [
    local_maintenance
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t