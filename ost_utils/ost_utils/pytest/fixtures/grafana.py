#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import pytest


@pytest.fixture(scope="session")
def grafana_admin_username():
    return "admin"


@pytest.fixture(scope="session")
def grafana_admin_password():
    return "123"


@pytest.fixture(scope="session")
def grafana_admin_api(
    engine_ip_url, grafana_admin_username, grafana_admin_password
):
    return "http://{}:{}@{}/ovirt-engine-grafana/api".format(
        grafana_admin_username, grafana_admin_password, engine_ip_url
    )
