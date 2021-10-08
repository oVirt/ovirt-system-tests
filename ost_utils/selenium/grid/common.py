#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import contextlib
import json
import os
import time

from ost_utils.shell import shell
from ost_utils.shell import ShellError


GRID_STARTUP_WAIT_RETRIES = 300
GRID_URL_TEMPLATE = "http://{}:{}/wd/hub"


class SeleniumGridError(Exception):
    pass


def grid_health_check(hub_url, expected_node_count=None):
    status_url = hub_url + "/status"

    for i in range(GRID_STARTUP_WAIT_RETRIES):
        try:
            out = shell(["curl", "-sSL", status_url])
            if json.loads(out)["value"]["ready"] is True:
                break
        except ShellError:
            pass
        time.sleep(0.1)
    else:
        raise SeleniumGridError("Selenium grid didn't start up properly")

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
            raise SeleniumGridError("Not enough nodes in selenium grid")


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
