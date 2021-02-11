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

import functools
import os
import tempfile
import time

import ovirtsdk4 as sdk4
import pytest

from ost_utils import assertions
from ost_utils import network_utils
from ost_utils.shell import shell
from ost_utils.shell import ShellError
from ost_utils.pytest.fixtures.ansible import ansible_engine
from ost_utils.pytest.fixtures.ansible import ansible_engine_facts
from ost_utils.pytest.fixtures.network import management_network_name
from ost_utils.pytest.fixtures.network import storage_network_name
from ost_utils.selenium.grid.common import http_proxy_disabled


@pytest.fixture(scope="session")
def engine_ips_for_network(ansible_engine_facts):
    return functools.partial(network_utils.get_ips, ansible_engine_facts)


@pytest.fixture(scope="session")
def engine_ip(engine_ips_for_network, management_network_name):
    return engine_ips_for_network(management_network_name)[0]


@pytest.fixture(scope="session")
def engine_storage_ips(engine_ips_for_network, storage_network_name):
    return engine_ips_for_network(storage_network_name)


@pytest.fixture(scope="session")
def engine_hostname(ansible_engine_facts):
    return ansible_engine_facts.get("ansible_hostname")


@pytest.fixture(scope="session")
def engine_fqdn(ansible_engine_facts):
    if 'he' in os.environ.get('SUITE_NAME'):
        return ansible_engine_facts.get("ansible_fqdn")
    else:
        # TODO:
        # Currently, basic-suite-master and a few others are using
        # fqdn 'engine'. Convert them to use a real fqdn created by
        # the backend and then remove the else part.
        return "engine"


@pytest.fixture(scope="session")
def engine_webadmin_url(engine_fqdn):
    return "https://%s/ovirt-engine" % engine_fqdn


@pytest.fixture(scope="session")
def engine_username():
    return "admin"


@pytest.fixture(scope="session")
def engine_full_username():
    return "admin@internal"


@pytest.fixture(scope="session")
def engine_email():
    return "root@localhost"


@pytest.fixture(scope="session")
def engine_password():
    # TODO: read the password from the answerfile
    return "123"


@pytest.fixture(scope="session")
def engine_api(engine_full_username, engine_password, engine_ip):
    url = 'https://{}/ovirt-engine/api'.format(engine_ip)
    api = sdk4.Connection(
        url=url,
        username=engine_full_username,
        password=engine_password,
        insecure=True,
        debug=True,
    )
    for _ in range(20):
        if not api.test():
            time.sleep(1)
        else:
            return api
    raise RuntimeError("Test API call failed")


@pytest.fixture(scope="session")
def engine_cert(engine_fqdn, engine_ip):
    with http_proxy_disabled():
        with tempfile.NamedTemporaryFile(prefix="engine-cert",
                                         suffix=".pem") as cert_file:
            shell([
                "curl", "-fsS",
                "-m", "10",
                "--resolve", "{}:80:{}".format(engine_fqdn, engine_ip),
                "-o", cert_file.name,
                "http://{}/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA".format(engine_fqdn)
            ])
            yield cert_file.name


@pytest.fixture(scope="session")
def engine_download(request, engine_fqdn, engine_ip):

    def download(url, path=None, timeout=10):
        args = ["curl", "-fsS", "-m", str(timeout)]

        if url.startswith("https"):
            args.extend([
                "--resolve", "{}:443:{}".format(engine_fqdn, engine_ip),
                "--cacert", request.getfixturevalue("engine_cert")
            ])
        else:
            args.extend([
                "--resolve", "{}:80:{}".format(engine_fqdn, engine_ip),
            ])

        if path is not None:
            args.extend(["-o", path])

        args.append(url)

        return shell(args, bytes_output=True)

    return download


@pytest.fixture(scope="session")
def engine_restart(ansible_engine, engine_download, engine_fqdn):

    def restart():
        ansible_engine.systemd(name='ovirt-engine', state='stopped')
        ansible_engine.systemd(name='ovirt-engine', state='started')

        health_url = 'http://{}/ovirt-engine/services/health'.format(engine_fqdn)

        def engine_is_alive():
            with http_proxy_disabled():
                engine_download(health_url)
                return True

        assertions.assert_true_within_short(engine_is_alive,
                                            allowed_exceptions=[ShellError])

    return restart
