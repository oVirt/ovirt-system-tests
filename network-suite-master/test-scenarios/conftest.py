# Copyright 2017-2020 Red Hat, Inc.
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

from fixtures.ansible import host0_facts  # NOQA: F401
from fixtures.ansible import host1_facts  # NOQA: F401
from fixtures.ansible import engine_facts  # NOQA: F401
from fixtures.ansible import ansible_engine  # NOQA: F401
from fixtures.ansible import ansible_clean_private_dirs  # NOQA: F401

from fixtures.ansible import ansible_collect_logs  # NOQA: F401

from fixtures.cluster import default_cluster  # NOQA: F401

from fixtures.network import ovirtmgmt_network  # NOQA: F401
from fixtures.network import ovirtmgmt_vnic_profile  # NOQA: F401

from fixtures.host import host_0  # NOQA: F401
from fixtures.host import host_1  # NOQA: F401
from fixtures.host import host_0_up  # NOQA: F401
from fixtures.host import host_1_up  # NOQA: F401
from fixtures.host import install_hosts_to_save_time  # NOQA: F401

from fixtures.engine import engine_full_username  # NOQA: F401
from fixtures.engine import engine_password  # NOQA: F401
from fixtures.engine import ovirt_engine_service_up  # NOQA: F401
from fixtures.engine import api  # NOQA: F401
from fixtures.engine import test_invocation_logger  # NOQA: F401

from fixtures.fqdn import fqdn  # NOQA: F401
from fixtures.fqdn import engine_storage_ipv6  # NOQA: F401
from fixtures.fqdn import host0_eth1_ipv6  # NOQA: F401
from fixtures.fqdn import host0_eth2_ipv6  # NOQA: F401

from fixtures.storage import default_storage_domain  # NOQA: F401
from fixtures.storage import lun_id  # NOQA: F401

from fixtures.providers import ovirt_image_repo  # NOQA: F401

from fixtures.virt import cirros_template  # NOQA: F401

from fixtures.data_center import data_centers_service  # NOQA: F401
from fixtures.data_center import default_data_center  # NOQA: F401

from fixtures.system import system  # NOQA: F401

# Import OST utils fixtures
from ost_utils.pytest.fixtures.artifacts import artifacts_dir  # NOQA: F401
from ost_utils.pytest.fixtures.artifacts import collect_artifacts  # NOQA: F401
from ost_utils.pytest.fixtures.virt import cirros_image  # NOQA: F401
from ost_utils.pytest.fixtures.virt import (  # NOQA: F401
    transformed_cirros_image,
)
