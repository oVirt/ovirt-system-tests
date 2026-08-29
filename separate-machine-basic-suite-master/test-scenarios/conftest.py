# -*- coding: utf-8 -*-
#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

import pytest

from ost_utils import network_utils

from ost_utils.pytest import pytest_collection_modifyitems

from ost_utils.pytest.fixtures import root_password

from ost_utils.pytest.fixtures.ansible import ansible_all
from ost_utils.pytest.fixtures.ansible import ansible_by_hostname
from ost_utils.pytest.fixtures.ansible import ansible_clean_private_dirs
from ost_utils.pytest.fixtures.ansible import ansible_collect_logs
from ost_utils.pytest.fixtures.ansible import ansible_engine
from ost_utils.pytest.fixtures.ansible import ansible_engine_facts
from ost_utils.pytest.fixtures.ansible import ansible_dwh
from ost_utils.pytest.fixtures.ansible import ansible_dwh_facts
from ost_utils.pytest.fixtures.ansible import ansible_host0_facts
from ost_utils.pytest.fixtures.ansible import ansible_host0
from ost_utils.pytest.fixtures.ansible import ansible_host1
from ost_utils.pytest.fixtures.ansible import ansible_hosts
from ost_utils.pytest.fixtures.ansible import ansible_inventory
from ost_utils.pytest.fixtures.ansible import ansible_storage
from ost_utils.pytest.fixtures.ansible import ansible_storage_facts

from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.artifacts import collect_artifacts
from ost_utils.pytest.fixtures.artifacts import collect_vdsm_coverage_artifacts
from ost_utils.pytest.fixtures.artifacts import dump_dhcp_leases
from ost_utils.pytest.fixtures.artifacts import generate_sar_stat_plots

from ost_utils.pytest.fixtures.backend import all_hostnames
from ost_utils.pytest.fixtures.backend import backend
from ost_utils.pytest.fixtures.backend import backend_engine_hostname
from ost_utils.pytest.fixtures.backend import backend_dwh_hostname
from ost_utils.pytest.fixtures.backend import deploy_scripts
from ost_utils.pytest.fixtures.backend import host0_hostname
from ost_utils.pytest.fixtures.backend import host1_hostname
from ost_utils.pytest.fixtures.backend import hosts_hostnames
from ost_utils.pytest.fixtures.backend import management_network_supports_ipv4
from ost_utils.pytest.fixtures.backend import storage_hostname

from ost_utils.pytest.fixtures.defaults import *

from ost_utils.pytest.fixtures.deployment import deploy
from ost_utils.pytest.fixtures.deployment import run_scripts
from ost_utils.pytest.fixtures.deployment import set_sar_interval

from ost_utils.pytest.fixtures.engine import *

from ost_utils.pytest.fixtures.grafana import *

from ost_utils.pytest.fixtures.keycloak import *

from ost_utils.pytest.fixtures.env import ost_images_distro
from ost_utils.pytest.fixtures.env import root_dir
from ost_utils.pytest.fixtures.env import ssh_key_file
from ost_utils.pytest.fixtures.env import suite_dir
from ost_utils.pytest.fixtures.env import working_dir
from ost_utils.pytest.fixtures.env import master_storage_domain_type

from ost_utils.pytest.fixtures.network import bonding_network_name
from ost_utils.pytest.fixtures.network import management_gw_ip
from ost_utils.pytest.fixtures.network import management_network_name

from ost_utils.pytest.fixtures.node import *

from ost_utils.pytest.fixtures.sdk import *

from ost_utils.pytest.fixtures.storage import *

from ost_utils.pytest.running_time import *


@pytest.fixture(scope="session")
def sd_iscsi_host_ip(storage_ips_for_network, storage_network_name):  # pylint: disable=function-redefined
    return storage_ips_for_network(storage_network_name)[0]


@pytest.fixture(scope="session")
def sd_nfs_host_storage_name(
    storage_hostname,
):  # pylint: disable=function-redefined
    return storage_hostname


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host(
    ansible_storage,
):  # pylint: disable=function-redefined
    return ansible_storage


@pytest.fixture(scope="session")
def engine_db_password():
    return 'engine_db_password123'


@pytest.fixture(scope="session")
def dwh_fqdn(ansible_dwh_facts, suite):
    return ansible_dwh_facts.get("ansible_fqdn")


@pytest.fixture(scope="session")
def grafana_fqdn(
    dwh_fqdn,
):  # pylint: disable=function-redefined
    return dwh_fqdn


@pytest.fixture(scope="session")
def engine_answer_file_contents(
    engine_password,
    engine_fqdn,
    engine_full_username,
    engine_db_password,
):  # pylint: disable=function-redefined
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
        f'OVESETUP_DB/password=str:{engine_db_password}\n'
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
        'OVESETUP_DWH_CORE/enable=bool:False\n'
        'QUESTION/1/OVESETUP_GRAFANA_ENABLE=str:no\n'
        f'OVESETUP_OVN/ovirtProviderOvnUser=str:{engine_full_username}\n'
        f'OVESETUP_OVN/ovirtProviderOvnPassword=str:{engine_password}\n'
        'OVESETUP_CONFIG/imageioProxyConfig=bool:True\n'
        'QUESTION/1/ovirt-cinderlib-enable=str:yes\n'
    )


@pytest.fixture(scope="session")
def dwh_answer_file_contents(
    engine_password,
    engine_fqdn,
    dwh_fqdn,
    root_password,
    engine_db_password,
    engine_full_username,
):  # pylint: disable=function-redefined
    return (
        '# action=setup\n'
        '[environment:default]\n'
        'QUESTION/1/OVESETUP_ENGINE_ENABLE=str:no\n'
        'QUESTION/1/OVESETUP_DWH_SCALE=str:2\n'
        'QUESTION/1/OVESETUP_ENGINE_DB_DATABASE=str:engine\n'
        f'QUESTION/1/OVESETUP_ENGINE_DB_HOST=str:{engine_fqdn}\n'
        f'QUESTION/1/OVESETUP_ENGINE_DB_PASSWORD=str:{engine_db_password}\n'
        'QUESTION/1/OVESETUP_ENGINE_DB_PORT=str:5432\n'
        'QUESTION/1/OVESETUP_ENGINE_DB_SECURED=str:no\n'
        'QUESTION/1/OVESETUP_ENGINE_DB_USER=str:engine\n'
        f'QUESTION/1/OVESETUP_NETWORK_FQDN_the_engine=str:{engine_fqdn}\n'
        f'QUESTION/1/OVESETUP_NETWORK_FQDN_this=str:{dwh_fqdn}\n'
        f'QUESTION/1/SSH_ACCESS_REMOTE_ENGINE_PASSWORD=str:{root_password}\n'
        f'QUESTION/1/queryEnvKey_input_OVESETUP_GRAFANA_CONFIG/adminPassword=str:{root_password}\n'
        f'QUESTION/1/queryEnvKey_input_second_password=str:{root_password}\n'
        'QUESTION/1/queryEnvKey_warnverify_OVESETUP_GRAFANA_CONFIG/adminPassword=str:yes\n'
        'QUESTION/1/ovirt-provider-ovn=str:no\n'
        'QUESTION/1/OVESETUP_CONFIG_WEBSOCKET_PROXY=str:no\n'
    )


@pytest.fixture(scope="session")
def dwh_answer_file_path(dwh_answer_file_contents, working_dir):
    file_path = os.path.join(working_dir, 'dwh-answer-file')
    with open(file_path, 'w') as f:
        f.write(dwh_answer_file_contents)
    return file_path
