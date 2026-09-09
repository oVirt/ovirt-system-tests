#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

import pytest


@pytest.fixture(scope="session")
def sd_iscsi_host_ip(engine_storage_ips):  # pylint: disable=function-redefined
    return engine_storage_ips[0]


@pytest.fixture(scope="session")
def sd_nfs_host_storage_name(engine_hostname):  # pylint: disable=function-redefined
    return engine_hostname


@pytest.fixture(scope="session")
def sd_iscsi_ansible_host(ansible_engine):  # pylint: disable=function-redefined
    return ansible_engine


@pytest.fixture(scope="session")
def is_node_suite():  # pylint: disable=function-redefined
    return True
