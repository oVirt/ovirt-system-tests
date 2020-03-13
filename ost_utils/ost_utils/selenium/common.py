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

import contextlib
import json
import os
import time

from ost_utils.shell import shell
from ost_utils.shell import ShellError


GRID_STARTUP_WAIT_RETRIES = 300
GRID_URL_TEMPLATE = "http://{}:{}/wd/hub"


def grid_health_check(hub_url, expected_node_count=None):
    status_url = hub_url + "/status"

    for i in range(GRID_STARTUP_WAIT_RETRIES):
        try:
            out = shell(["curl", "-sSL", status_url])
            if json.loads(out)["value"]["ready"] == True:
                break
        except ShellError:
            pass
        time.sleep(0.1)
    else:
        raise RuntimeError("Selenium grid didn't start up properly")

    if expected_node_count is not None:
        api_url = "/".join(hub_url.split("/")[:-2] + ["grid/api/hub"])

        for i in range(GRID_STARTUP_WAIT_RETRIES):
            try:
                out = shell(["curl", "-sSL", api_url])
                node_count = json.loads(out)["slotCounts"]["total"]
                if node_count == expected_node_count:
                    break
            except ShellError:
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("Not enough nodes in selenium grid")


@contextlib.contextmanager
def http_proxy_disabled():
    # proxy is used in CI -- turn off proxy for webdriver
    # TODO is there a better way, perhaps via webdriver api?
    old_proxy = os.environ.get("http_proxy", None)
    os.environ["http_proxy"] = ""
    try:
        yield
    finally:
        if old_proxy is not None:
            os.environ["http_proxy"] = old_proxy
