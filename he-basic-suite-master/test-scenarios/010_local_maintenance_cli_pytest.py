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
    attempt = 5
    failed = False
    while not failed:
        attempt -= 1
        ret = host.ssh(["hosted-engine", "--vm-status", "--json"])
        nt.assert_equals(ret.code, 0)
        try:
            return json.loads(ret.out)
        except ValueError:
            if attempt <= 0:
                failed = True
    raise RuntimeError('could not parse JSON: %s' % ret.out)


@testlib.with_ovirt_prefix
def local_maintenance(prefix):
    logging.info("Waiting For System Stability...")
    time.sleep(wait_value)

    hosts = prefix.virt_env.host_vms()
    hevm_index, hevm_host = _find_host_running_he_vm(hosts)

    nonhevm_host = next(h for h in hosts if h.name() != hevm_host.name())

    # TODO: check why it fails
    #ret = hevm_host.ssh([
    #    "hosted-engine", "--set-maintenance", "--mode=local"])
    #nt.assert_not_equal(ret.code, 0)

    ret = nonhevm_host.ssh([
        "hosted-engine", "--set-maintenance", "--mode=local"])
    nt.assert_equals(ret.code, 0)

    ret = nonhevm_host.ssh(["hosted-engine", "--set-maintenance", "--mode=none"])
    nt.assert_equals(ret.code, 0)


_TEST_LIST = [
    local_maintenance
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
