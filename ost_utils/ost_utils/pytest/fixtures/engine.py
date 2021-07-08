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
from ost_utils.pytest.fixtures.network import management_network_name
from ost_utils.pytest.fixtures.network import storage_network_name
from ost_utils.selenium.grid.common import http_proxy_disabled


@pytest.fixture(scope="session")
def engine_ips_for_network(ansible_engine_facts, backend):
    return functools.partial(network_utils.get_ips, backend, ansible_engine_facts)


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
    elif 'hc' in os.environ.get('SUITE_NAME'):
        return "lago-hc-basic-suite-master-engine.lago.local"
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
def engine_api_url(engine_ip):
    return 'https://{}/ovirt-engine/api'.format(engine_ip)


@pytest.fixture(scope="session")
def nonadmin_username():
    return "non_admin_user"


@pytest.fixture(scope="session")
def nonadmin_password():
    return "123456"


@pytest.fixture(scope="session")
def engine_api(engine_full_username, engine_password, engine_api_url):
    api = sdk4.Connection(
        url=engine_api_url,
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


@pytest.fixture(scope="session")
def engine_answer_file_contents(engine_password, engine_fqdn):
    return ('# action=setup\n'
            '[environment:default]\n'
            'OVESETUP_DIALOG/confirmSettings=bool:True\n'
            'OVESETUP_CONFIG/applicationMode=str:both\n'
            'OVESETUP_CONFIG/remoteEngineSetupStyle=none:None\n'
            f'OVESETUP_CONFIG/adminPassword=str:{engine_password}\n'
            'OVESETUP_CONFIG/storageIsLocal=bool:False\n'
            'OVESETUP_CONFIG/firewallManager=str:firewalld\n'
            'OVESETUP_CONFIG/remoteEngineHostRootPassword=none:None\n'
            'OVESETUP_CONFIG/firewallChangesReview=none:None\n'
            'OVESETUP_CONFIG/updateFirewall=bool:True\n'
            'OVESETUP_CONFIG/remoteEngineHostSshPort=none:None\n'
            f'OVESETUP_CONFIG/fqdn=str:{engine_fqdn}\n'
            'OVESETUP_CONFIG/storageType=none:None\n'
            'OSETUP_RPMDISTRO/requireRollback=none:None\n'
            'OSETUP_RPMDISTRO/enableUpgrade=bool:True\n'
            'OVESETUP_DB/database=str:engine\n'
            'OVESETUP_DB/fixDbViolations=none:None\n'
            'OVESETUP_DB/secured=bool:False\n'
            'OVESETUP_DB/host=str:localhost\n'
            'OVESETUP_DB/user=str:engine\n'
            'OVESETUP_DB/securedHostValidation=bool:False\n'
            'OVESETUP_DB/port=int:5432\n'
            'OVESETUP_ENGINE_CORE/enable=bool:True\n'
            'OVESETUP_CORE/engineStop=none:None\n'
            'OVESETUP_SYSTEM/memCheckEnabled=bool:False\n'
            'OVESETUP_SYSTEM/nfsConfigEnabled=bool:False\n'
            'OVESETUP_PKI/organization=str:Test\n'
            'OVESETUP_CONFIG/isoDomainMountPoint=none:None\n'
            'OVESETUP_CONFIG/isoDomainName=none:None\n'
            'OVESETUP_CONFIG/isoDomainACL=none:None\n'
            'OVESETUP_AIO/configure=none:None\n'
            'OVESETUP_AIO/storageDomainName=none:None\n'
            'OVESETUP_AIO/storageDomainDir=none:None\n'
            'OVESETUP_PROVISIONING/postgresProvisioningEnabled=bool:True\n'
            'OVESETUP_APACHE/configureRootRedirection=bool:True\n'
            'OVESETUP_APACHE/configureSsl=bool:True\n'
            'OVESETUP_CONFIG/websocketProxyConfig=bool:True\n'
            f'OVESETUP_ENGINE_CONFIG/fqdn=str:{engine_fqdn}\n'
            'OVESETUP_CONFIG/sanWipeAfterDelete=bool:False\n'
            'OVESETUP_VMCONSOLE_PROXY_CONFIG/vmconsoleProxyConfig=bool:True\n'
            'OVESETUP_DWH_CORE/enable=bool:True\n'
            'OVESETUP_DWH_CONFIG/dwhDbBackupDir=str:/var/lib/ovirt-engine-dwh/backups\n'
            'OVESETUP_DWH_DB/database=str:ovirt_engine_history\n'
            'OVESETUP_DWH_DB/disconnectExistingDwh=none:None\n'
            'OVESETUP_DWH_DB/dumper=str:pg_custom\n'
            'OVESETUP_DWH_DB/filter=none:None\n'
            'OVESETUP_DWH_DB/host=str:localhost\n'
            'OVESETUP_DWH_DB/password=str:uf5vskEpdSeflQnwAdp4ZO\n'
            'OVESETUP_DWH_DB/performBackup=none:None\n'
            'OVESETUP_DWH_DB/port=int:5432\n'
            'OVESETUP_DWH_DB/restoreBackupLate=bool:True\n'
            'OVESETUP_DWH_DB/restoreJobs=int:2\n'
            'OVESETUP_DWH_DB/secured=bool:False\n'
            'OVESETUP_DWH_DB/securedHostValidation=bool:False\n'
            'OVESETUP_DWH_DB/user=str:ovirt_engine_history\n'
            'OVESETUP_DWH_PROVISIONING/postgresProvisioningEnabled=bool:True\n'
            'OVESETUP_DWH_CONFIG/scale=str:1\n'
            'OVESETUP_OVN/ovirtProviderOvnUser=str:admin@internal\n'
            f'OVESETUP_OVN/ovirtProviderOvnPassword=str:{engine_password}\n'
            'OVESETUP_CONFIG/imageioProxyConfig=bool:True\n')


@pytest.fixture(scope="session")
def engine_answer_file_path(engine_answer_file_contents, artifacts_dir):
    file_path = f'{artifacts_dir}/answer-file'
    with open(file_path, 'w') as f:
        f.write(engine_answer_file_contents)
    return file_path
