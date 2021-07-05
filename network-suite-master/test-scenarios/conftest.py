# Copyright 2017-2021 Red Hat, Inc.
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

from fixtures.ansible import host0_facts
from fixtures.ansible import host1_facts
from fixtures.ansible import engine_facts
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

from fixtures.engine import engine_full_username
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

from fixtures.providers import ovirt_image_repo

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
from ost_utils.pytest.fixtures.ansible import ansible_inventory
from ost_utils.pytest.fixtures.ansible import ansible_storage
from ost_utils.pytest.fixtures.artifacts import artifacts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.artifacts import artifact_list
from ost_utils.pytest.fixtures.artifacts import collect_artifacts
from ost_utils.pytest.fixtures.backend import all_hostnames
from ost_utils.pytest.fixtures.backend import backend
from ost_utils.pytest.fixtures.backend import backend_engine_hostname
from ost_utils.pytest.fixtures.backend import deploy_scripts
from ost_utils.pytest.fixtures.backend import host0_hostname
from ost_utils.pytest.fixtures.backend import host1_hostname
from ost_utils.pytest.fixtures.backend import hosts_hostnames
from ost_utils.pytest.fixtures.defaults import ansible_vms_to_deploy
from ost_utils.pytest.fixtures.deployment import deploy
from ost_utils.pytest.fixtures.deployment import run_scripts
from ost_utils.pytest.fixtures.env import working_dir
from ost_utils.pytest.fixtures.virt import cirros_image
from ost_utils.pytest.fixtures.virt import transformed_cirros_image
