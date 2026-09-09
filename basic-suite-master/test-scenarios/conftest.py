#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

import pytest


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
