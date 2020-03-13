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

import tempfile

import pytest

from ost_utils.shell import shell
from ost_utils.pytest.fixtures import prefix


@pytest.fixture(scope="session")
def engine_ip(prefix):
    engine = prefix.virt_env.engine_vm()
    return engine.ip()


@pytest.fixture(scope="session")
def engine_fqdn():
    return "engine"


@pytest.fixture(scope="session")
def engine_webadmin_url(engine_fqdn):
    return "https://%s/ovirt-engine/webadmin" % engine_fqdn


@pytest.fixture(scope="session")
def engine_username():
    return "admin"


@pytest.fixture(scope="session")
def engine_password(prefix):
    engine = prefix.virt_env.engine_vm()
    return engine.metadata["ovirt-engine-password"]


@pytest.fixture(scope="session")
def engine_cert(engine_ip):
    with tempfile.NamedTemporaryFile(prefix="engine-cert",
                                     suffix=".pem", delete=False) as cert_file:
        url = "https://%s/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA" % engine_ip
        shell(["curl", "--insecure", "--output", cert_file.name, url])
        yield cert_file.name
