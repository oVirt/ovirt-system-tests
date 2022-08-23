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
    return "badpass-1"


@pytest.fixture(scope="session")
def engine_api_url(engine_ip_url):
    return f'https://{engine_ip_url}/ovirt-engine/api'


@pytest.fixture(scope="session")
def nonadmin_username():
    return "non_admin_user"


@pytest.fixture(scope="session")
def nonadmin_password():
    return "non_admin_password"


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
        'OVESETUP_SYSTEM/memCheckEnabled=bool:False\n'
        f'OVESETUP_OVN/ovirtProviderOvnUser=str:{engine_full_username}\n'
        'QUESTION/1/ovirt-cinderlib-enable=str:yes\n'
        'QUESTION/1/OVESETUP_CONFIG_APPLICATION_MODE=str:both\n'
        'QUESTION/1/GRAFANA_USE_ENGINE_ADMIN_PASSWORD=str:no\n'
        'QUESTION/1/KEYCLOAK_USE_ENGINE_ADMIN_PASSWORD=str:no\n'
        'QUESTION/1/OVESETUP_CONFIG_ADMIN_SETUP=str:badpass-2\n'
        'QUESTION/2/OVESETUP_CONFIG_ADMIN_SETUP=str:badpass-3\n'
        'QUESTION/3/OVESETUP_CONFIG_ADMIN_SETUP=str:badpass-1\n'
        'QUESTION/4/OVESETUP_CONFIG_ADMIN_SETUP=str:badpass-1\n'
        'QUESTION/1/OVESETUP_CONFIG_WEAK_ENGINE_PASSWORD=str:yes\n'
        'QUESTION/1/OVESETUP_DWH_PROVISIONING_POSTGRES_ENABLED=str:manual\n'
        'QUESTION/1/OVESETUP_DWH_PROVISIONING_POSTGRES_LOCATION=str:local\n'
        'QUESTION/1/OVESETUP_DWH_DB_DATABASE=str:ovirt_engine_history\n'
        'QUESTION/1/OVESETUP_DWH_DB_PASSWORD=str:badpass-4\n'
        'QUESTION/1/OVESETUP_DWH_DB_SECURED=str:no\n'
        'QUESTION/1/OVESETUP_DWH_DB_USER=str:ovirt_engine_history\n'
        'QUESTION/1/OVESETUP_DWH_ENABLE=str:yes\n'
        'QUESTION/1/OVESETUP_DWH_SCALE=str:1\n'
        'QUESTION/1/OVESETUP_PROVISIONING_POSTGRES_ENABLED=str:manual\n'
        'QUESTION/1/OVESETUP_PROVISIONING_POSTGRES_LOCATION=str:local\n'
        'QUESTION/1/OVESETUP_ENGINE_DB_DATABASE=str:engine\n'
        'QUESTION/1/OVESETUP_ENGINE_DB_PASSWORD=str:badpass-5\n'
        'QUESTION/1/OVESETUP_ENGINE_DB_SECURED=str:no\n'
        'QUESTION/1/OVESETUP_ENGINE_DB_USER=str:engine\n'
        'QUESTION/1/OVESETUP_ENGINE_ENABLE=str:yes\n'
        'QUESTION/1/OVESETUP_GRAFANA_DB_PASSWORD=str:badpass-6\n'
        'QUESTION/1/OVESETUP_GRAFANA_DB_USER=str:ovirt_engine_history_grafana\n'
        'QUESTION/1/OVESETUP_GRAFANA_ENABLE=str:yes\n'
        'QUESTION/1/OVESETUP_KEYCLOAK_DB_DATABASE=str:ovirt_engine_keycloak\n'
        'QUESTION/1/OVESETUP_KEYCLOAK_DB_PASSWORD=str:badpass-7\n'
        'QUESTION/1/OVESETUP_KEYCLOAK_DB_SECURED=str:no\n'
        'QUESTION/1/OVESETUP_KEYCLOAK_DB_USER=str:ovirt_engine_keycloak\n'
        'QUESTION/1/OVESETUP_KEYCLOAK_ENABLE=str:yes\n'
        'QUESTION/1/OVESETUP_KEYCLOAK_PROVISIONING_POSTGRES_ENABLED=str:manual\n'
        'QUESTION/1/OVESETUP_KEYCLOAK_PROVISIONING_POSTGRES_LOCATION=str:local\n'
        f'QUESTION/1/OVESETUP_NETWORK_FQDN_this=str:{engine_fqdn}\n'
        'QUESTION/1/OVESETUP_PKI_ORG=str:Test\n'
        'QUESTION/1/OVESETUP_UPDATE_FIREWALL=str:yes\n'
        'QUESTION/1/ovirt-provider-ovn=str:yes\n'
        f'QUESTION/1/queryEnvKey_input_OVESETUP_CONFIG/keycloakAdminPasswd=str:{keycloak_admin_password}\n'
        f'QUESTION/1/queryEnvKey_input_second_password=str:{keycloak_admin_password}\n'
        'QUESTION/1/queryEnvKey_warnverify_OVESETUP_CONFIG/keycloakAdminPasswd=str:yes\n'
        'QUESTION/1/queryEnvKey_input_OVESETUP_GRAFANA_CONFIG/adminPassword=str:badpass-9\n'
        'QUESTION/2/queryEnvKey_input_second_password=str:badpass-9\n'
        'QUESTION/1/queryEnvKey_warnverify_OVESETUP_GRAFANA_CONFIG/adminPassword=str:yes\n'
        'QUESTION/1/OVESETUP_DIALOG_CONFIRM_SETTINGS=str:ok\n'
    )


@pytest.fixture(scope="session")
def engine_answer_file_path(engine_answer_file_contents, working_dir):
    file_path = os.path.join(working_dir, 'engine-answer-file')
    with open(file_path, 'w') as f:
        f.write(engine_answer_file_contents)
    return file_path
