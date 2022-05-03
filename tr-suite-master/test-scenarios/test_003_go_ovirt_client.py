#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

from os import environ, path

from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.env import suite_dir

def test_run_go_ovirt_client_tests(ansible_engine, engine_api_url,
                           engine_full_username, engine_password):

    ansible_engine.shell(
        f'OVIRT_CA_FILE=/etc/pki/ovirt-engine/ca.pem OVIRT_URL={engine_api_url} OVIRT_USERNAME={engine_full_username} OVIRT_PASSWRD={engine_password} go-ovirt-client-tests-exe -test.v'
    )

