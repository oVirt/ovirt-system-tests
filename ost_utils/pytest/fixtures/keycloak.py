#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import pytest


@pytest.fixture(scope="session")
def keycloak_auth_url(engine_fqdn):
    return f"https://{engine_fqdn}/ovirt-engine-auth"


@pytest.fixture(scope="session")
def keycloak_admin_username():
    return "admin"


@pytest.fixture(scope="session")
def keycloak_admin_password(engine_password):
    # By default password is the same as admin administrator password
    return engine_password


@pytest.fixture(scope="session")
def keycloak_ovirt_realm():
    return "ovirt-internal"


@pytest.fixture(scope="session")
def keycloak_profile():
    return "internalsso"


@pytest.fixture(scope="session")
def keycloak_master_realm():
    return "master"
