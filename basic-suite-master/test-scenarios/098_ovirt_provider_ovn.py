#
# Copyright 2017 Red Hat, Inc.
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

import json
import requests
import uuid

import nose.tools as nt

from ovirtlago import testlib


OVN_PROVIDER_TOKEN_URL = 'https://{hostname}:35357/v2.0/tokens'
OVN_PROVIDER_NETWORKS_URL = 'https://{hostname}:9696/v2.0/networks'


def _request_auth_token(engine_name):
    auth_request_data = {
        "auth": {
            "tenantName": "ovirt-provider-ovn",
            "passwordCredentials": {
                "username": "admin@internal",
                "password": "123"
            }
        }
    }
    response = requests.post(
        OVN_PROVIDER_TOKEN_URL.format(
            hostname=engine_name
        ),
        data=json.dumps(auth_request_data),
        verify=False)
    return response.json()


def _get_auth_token(engine_name):
    response_json = _request_auth_token(engine_name)
    token_id = response_json['access']['token']['id']
    return token_id


def _get_networks(token_id, engine_name):
    response = requests.get(
        OVN_PROVIDER_NETWORKS_URL.format(
            hostname=engine_name
        ),
        verify=False,
        headers={
            'X-Auth-Token': token_id
        }
    )
    return response.json()


@testlib.with_ovirt_prefix
def test_ovn_provider_networks(prefix):
    engine = prefix.virt_env.engine_vm()
    engine_ip = engine.ip()
    token_id = _get_auth_token(engine_ip)
    networks = _get_networks(token_id, engine_ip)
    nt.assert_true(
        'networks' in networks
    )


_TEST_LIST = [
    test_ovn_provider_networks,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
