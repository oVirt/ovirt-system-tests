#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

from os import environ, path

from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.engine import *


def test_run_go_ovirt_client_tests(ansible_engine, engine_api, engine_fqdn, engine_api_url,
                           engine_full_username, engine_password, artifacts_dir):

    ansible_engine.shell("dnf install -y go-ovirt-client-tests")
    output_file = os.path.join(artifacts_dir, 'go-ovirt-client-tests.out')
    with open(output_file, 'w', encoding='utf-8') as o:
        out = ansible_engine.shell(
            f"OVIRT_CAFILE=/etc/pki/ovirt-engine/ca.pem \
              OVIRT_URL={engine_api_url} \
              OVIRT_USERNAME={engine_full_username} \
              OVIRT_PASSWORD={engine_password} \
              go-ovirt-client-tests-exe"
        )['stdout']
        o.write("%s\n" % out)
