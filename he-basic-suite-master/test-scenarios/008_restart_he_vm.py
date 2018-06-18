#
# Copyright 2016 Red Hat, Inc.
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

host_state = 8
index_value = 1

@testlib.with_ovirt_prefix
def set_global_maintenance(prefix):
    host = prefix.virt_env.host_vms()[0]
    ret = host.ssh(["hosted-engine", "--set-maintenance", "--mode=global"])
    nt.assert_equals(ret.code, 0)

    testlib.assert_true_within_short(
        lambda: _get_he_status(host)['global_maintenance'] is True
    )


@testlib.with_ovirt_prefix
def restart_he_vm(prefix):
    hosts = prefix.virt_env.host_vms()
    host = _find_host_running_he_vm(hosts)

    _shutdown_he_vm(host)
    _restart_services(host)
    _start_he_vm(host)
    _wait_for_engine_health(host)


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


@testlib.with_ovirt_prefix
def clear_global_maintenance(prefix):
    host = prefix.virt_env.host_vms()[0]

    ret = host.ssh(["hosted-engine", "--set-maintenance", "--mode=none"])
    nt.assert_equals(ret.code, 0)

    testlib.assert_true_within_short(
        lambda: _get_he_status(host)['global_maintenance'] is False
    )

    testlib.assert_true_within_long(
        lambda: _is_state_maintenance(host, "GlobalMaintenance") is False
    )


def _find_host_running_he_vm(hosts):
    status = _get_he_status(hosts[0])
    running_on = ""
    for k, v in status.items():
        if not k.isdigit():
            continue

        if v["engine-status"]["vm"] == "up":
            running_on = v["hostname"].split(".", 1)[0]
            break

    return next(h for h in hosts if h.name() == running_on)


def _get_he_status(host):
    ret = host.ssh(["hosted-engine", "--vm-status", "--json"])
    nt.assert_equals(ret.code, 0)

    try:
        return json.loads(ret.out)
    except ValueError:
        raise RuntimeError('could not parse JSON: %s' % ret.out)


def _shutdown_he_vm(host):
    logging.info("Shutting down HE VM on host: %s", host.name())
    ret = host.ssh(["hosted-engine", "--vm-shutdown"])
    nt.assert_equals(ret.code, 0)
    logging.info("Command succeeded")

    logging.info("Waiting for VM to be down...")

    testlib.assert_true_within_short(lambda: all(
        v["engine-status"]["vm"] != "up"
        for k, v in _get_he_status(host).items()
        if k.isdigit()
    ))

    logging.info("VM is down.")


def _restart_services(host):
    logging.info("Restarting services...")
    ret = host.ssh(["systemctl", "restart", "vdsmd", "ovirt-ha-broker", "ovirt-ha-agent"])
    nt.assert_equals(ret.code, 0)
    logging.info("Success.")

    logging.info("Waiting for agent to be ready...")

    testlib.assert_true_within_long(
        lambda: host.ssh(["hosted-engine", "--vm-status"]).code == 0
    )

    logging.info("Agent is ready.")


def _start_he_vm(host):
    logging.info("Starting VM...")
    ret = host.ssh(["hosted-engine", "--vm-start"])
    nt.assert_equals(ret.code, 0)
    logging.info("Command succeeded")

    logging.info("Waiting for VM to be UP...")

    testlib.assert_true_within_short(lambda: any(
        v["engine-status"]["vm"] == "up"
        for k, v in _get_he_status(host).items()
        if k.isdigit()
    ))

    logging.info("VM is UP.")


def _wait_for_engine_health(host):
    logging.info("Waiting for engine to start...")
    testlib.assert_true_within_long(lambda: any(
        v["engine-status"]["health"] == "good"
        for k, v in _get_he_status(host).items()
        if k.isdigit()
    ))

    logging.info("Engine is running.")


_TEST_LIST = [
    set_global_maintenance,
    restart_he_vm,
    clear_global_maintenance
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t

