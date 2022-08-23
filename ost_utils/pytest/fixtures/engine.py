#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import functools
import os
import tempfile
import time

import ovirtsdk4 as sdk4
import ovirtsdk4.types as types
import pytest

from ost_utils import assert_utils
from ost_utils import network_utils
from ost_utils.ansible import AnsibleExecutionError
from ost_utils.shell import shell
from ost_utils.shell import ShellError
from ost_utils.pytest.fixtures.env import suite
from ost_utils.pytest.fixtures.network import management_network_name
from ost_utils.pytest.fixtures.network import storage_network_name


@pytest.fixture(scope="session")
def engine_ips_for_network(ansible_engine_facts, backend):
    return functools.partial(network_utils.get_ips, backend, ansible_engine_facts)


@pytest.fixture(scope="session")
def engine_ip(engine_ips_for_network, management_network_name):
    return engine_ips_for_network(management_network_name)[0]


@pytest.fixture(scope="session")
def engine_ip_url(engine_ip):
    return network_utils.ip_to_url(engine_ip)


@pytest.fixture(scope="session")
def engine_storage_ips(engine_ips_for_network, storage_network_name):
    return engine_ips_for_network(storage_network_name)


@pytest.fixture(scope="session")
def engine_hostname(ansible_engine_facts):
    return ansible_engine_facts.get("ansible_hostname")


@pytest.fixture(scope="session")
def engine_fqdn(ansible_engine_facts, suite):
    return ansible_engine_facts.get("ansible_fqdn")


@pytest.fixture(scope="session")
def engine_webadmin_url(engine_fqdn):
    return "https://%s/ovirt-engine" % engine_fqdn


@pytest.fixture(scope="session")
def keycloak_enabled(ost_images_distro, suite):
    # internally bundled Keycloak authentication is by default (via engine-setup) enabled only for upstream (el8stream)
    # downstream (rhel) still depends on legacy AAA. Keycloak authentication can still be enabled manually
    return ost_images_distro != 'rhel8'


@pytest.fixture(scope="session")
def engine_username(keycloak_enabled):
    if keycloak_enabled:
        return "admin@ovirt"

    # use legacy AAA authentication for rhel
    return "admin"


@pytest.fixture(scope="session")
def engine_full_username(keycloak_enabled):
    if keycloak_enabled:
        return "admin@ovirt@internalsso"

    # use legacy AAA authentication for rhel
    return 'admin@internal'


@pytest.fixture(scope="session")
def engine_user_domain(keycloak_enabled):
    if keycloak_enabled:
        return types.Domain(name='internalkeycloak-authz')

    # use legacy AAA authentication for rhel
    return types.Domain(name='internal-authz')


@pytest.fixture(scope="session")
def engine_admin_service(get_user_service_for_user, engine_username):
    admin = get_user_service_for_user(engine_username)
    return admin


@pytest.fixture(scope="session")
def engine_password():
    return "123456"


@pytest.fixture(scope="session")
def engine_api_url(engine_ip_url):
    return f'https://{engine_ip_url}/ovirt-engine/api'


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
def engine_cert(engine_fqdn, engine_ip_url):
    with tempfile.NamedTemporaryFile(prefix="engine-cert", suffix=".pem") as cert_file:
        shell(
            [
                "curl",
                "-fsS",
                "-m",
                "10",
                "--resolve",
                "{}:80:{}".format(engine_fqdn, engine_ip_url),
                "-o",
                cert_file.name,
                "http://{}/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA".format(
                    engine_fqdn
                ),
            ]
        )
        yield cert_file.name


@pytest.fixture(scope="session")
def engine_download(request, engine_fqdn, engine_ip_url):
    def download(url, path=None, timeout=10):
        args = ["curl", "-fsS", "-m", str(timeout)]

        if url.startswith("https"):
            args.extend(
                [
                    "--resolve",
                    "{}:443:{}".format(engine_fqdn, engine_ip_url),
                    "--cacert",
                    request.getfixturevalue("engine_cert"),
                ]
            )
        else:
            args.extend(
                [
                    "--resolve",
                    "{}:80:{}".format(engine_fqdn, engine_ip_url),
                ]
            )

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
            engine_download(health_url)
            return True

        assert assert_utils.true_within_short(engine_is_alive, allowed_exceptions=[ShellError])

    return restart


@pytest.fixture(scope="session")
def engine_answer_file_contents(engine_password, keycloak_admin_password, engine_fqdn, engine_full_username):
    return (
        '# action=setup\n'
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
        f'OVESETUP_OVN/ovirtProviderOvnUser=str:{engine_full_username}\n'
        f'OVESETUP_OVN/ovirtProviderOvnPassword=str:{engine_password}\n'
        'OVESETUP_CONFIG/imageioProxyConfig=bool:True\n'
        'QUESTION/1/ovirt-cinderlib-enable=str:yes\n'
    )


@pytest.fixture(scope="session")
def engine_answer_file_path(engine_answer_file_contents, working_dir):
    file_path = os.path.join(working_dir, 'engine-answer-file')
    with open(file_path, 'w') as f:
        f.write(engine_answer_file_contents)
    return file_path
