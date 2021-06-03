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
        grafana_admin_username, grafana_admin_password, engine_ip_url)

