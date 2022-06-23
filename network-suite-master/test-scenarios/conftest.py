#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

from fixtures.ansible import af
from fixtures.ansible import host0_facts
from fixtures.ansible import host1_facts
from fixtures.ansible import engine_facts
from fixtures.ansible import storage_facts
from fixtures.ansible import ansible_clean_private_dirs

from fixtures.ansible import ansible_collect_logs

from fixtures.cluster import default_cluster

from fixtures.network import ovirtmgmt_network
from fixtures.network import ovirtmgmt_vnic_profile

from fixtures.host import host_0
from fixtures.host import host_1
from fixtures.host import host_0_up
from fixtures.host import host_1_up
from fixtures.host import install_hosts_to_save_time

from fixtures.engine import engine_password
from fixtures.engine import ovirt_engine_setup
from fixtures.engine import ovirt_engine_service_up
from fixtures.engine import api
from fixtures.engine import test_invocation_logger

from fixtures.fqdn import engine_storage_ipv6
from fixtures.fqdn import host0_eth1_ipv6
from fixtures.fqdn import host0_eth2_ipv6
from fixtures.fqdn import ovirt_provider_ovn_with_ip_fqdn

from fixtures.storage import default_storage_domain
from fixtures.storage import lun_id

from fixtures.virt import cirros_template

from fixtures.data_center import data_centers_service
from fixtures.data_center import default_data_center

from fixtures.system import system

# Import OST utils fixtures
from ost_utils.pytest.fixtures.ansible import ansible_all
from ost_utils.pytest.fixtures.ansible import ansible_by_hostname
from ost_utils.pytest.fixtures.ansible import ansible_engine
from ost_utils.pytest.fixtures.ansible import ansible_engine_facts
from ost_utils.pytest.fixtures.ansible import ansible_host0
from ost_utils.pytest.fixtures.ansible import ansible_host0_facts
from ost_utils.pytest.fixtures.ansible import ansible_host1
from ost_utils.pytest.fixtures.ansible import ansible_host1_facts
from ost_utils.pytest.fixtures.ansible import ansible_hosts
from ost_utils.pytest.fixtures.ansible import ansible_storage_facts
from ost_utils.pytest.fixtures.ansible import ansible_inventory
from ost_utils.pytest.fixtures.ansible import ansible_storage
from ost_utils.pytest.fixtures.artifacts import artifacts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.artifacts import artifact_list
from ost_utils.pytest.fixtures.artifacts import collect_artifacts
from ost_utils.pytest.fixtures.artifacts import dump_dhcp_leases
from ost_utils.pytest.fixtures.artifacts import generate_sar_stat_plots
from ost_utils.pytest.fixtures.backend import all_hostnames
from ost_utils.pytest.fixtures.backend import backend
from ost_utils.pytest.fixtures.backend import backend_engine_hostname
from ost_utils.pytest.fixtures.backend import deploy_scripts
from ost_utils.pytest.fixtures.backend import host0_hostname
from ost_utils.pytest.fixtures.backend import host1_hostname
from ost_utils.pytest.fixtures.backend import hosts_hostnames
from ost_utils.pytest.fixtures.backend import storage_hostname
from ost_utils.pytest.fixtures.backend import management_network_supports_ipv4
from ost_utils.pytest.fixtures.backend import tested_ip_version
from ost_utils.pytest.fixtures.defaults import deploy_hosted_engine
from ost_utils.pytest.fixtures.deployment import deploy
from ost_utils.pytest.fixtures.deployment import run_scripts
from ost_utils.pytest.fixtures.deployment import set_sar_interval
from ost_utils.pytest.fixtures.engine import engine_api
from ost_utils.pytest.fixtures.engine import engine_api_url
from ost_utils.pytest.fixtures.engine import engine_admin_service
from ost_utils.pytest.fixtures.engine import engine_answer_file_contents
from ost_utils.pytest.fixtures.engine import engine_answer_file_path
from ost_utils.pytest.fixtures.engine import engine_fqdn
from ost_utils.pytest.fixtures.engine import engine_full_username
from ost_utils.pytest.fixtures.engine import engine_ip
from ost_utils.pytest.fixtures.engine import engine_ip_url
from ost_utils.pytest.fixtures.engine import engine_ips_for_network
from ost_utils.pytest.fixtures.engine import engine_username
from ost_utils.pytest.fixtures.engine import keycloak_enabled
from ost_utils.pytest.fixtures.env import ost_images_distro
from ost_utils.pytest.fixtures.env import root_dir
from ost_utils.pytest.fixtures.env import ssh_key_file
from ost_utils.pytest.fixtures.env import suite
from ost_utils.pytest.fixtures.env import working_dir
from ost_utils.pytest.fixtures.network import management_network_name
from ost_utils.pytest.fixtures.network import management_subnet
from ost_utils.pytest.fixtures.network import storage_subnet
from ost_utils.pytest.fixtures.sdk import get_user_service_for_user
from ost_utils.pytest.fixtures.sdk import system_service
from ost_utils.pytest.fixtures.sdk import users_service
from ost_utils.pytest.fixtures.virt import cirros_image_template_name
from ost_utils.pytest.fixtures.virt import cirros_serial_console
from ost_utils.pytest.fixtures.virt import rsa_pair
