#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import pytest

from ovirtlib import sshlib

OVN_CONF = '/etc/ovirt-provider-ovn/conf.d/10-setup-ovirt-provider-ovn.conf'


class EngineNotResorvableError(Exception):
    pass


@pytest.fixture(scope='session')
def ovirt_provider_ovn_with_ip_fqdn(ovirt_engine_service_up, engine_facts, engine_answer_file_path):
    provider_ip = f'provider-host={engine_facts.default_ip(urlize=True)}'
    provider_fqdn = f'provider-host={_fetch_fqdn(engine_answer_file_path)}'
    engine = sshlib.Node(engine_facts.default_ip())
    try:
        engine.global_replace_str_in_file(provider_fqdn, provider_ip, OVN_CONF)
        engine.restart_service('ovirt-provider-ovn')
        yield
    finally:
        engine.global_replace_str_in_file(provider_ip, provider_fqdn, OVN_CONF)
        engine.restart_service('ovirt-provider-ovn')


def _fetch_fqdn(answer_file):
    FQDN_ENTRY = 'OVESETUP_CONFIG/fqdn'

    with open(answer_file) as f:
        for line in f:
            if line.startswith(FQDN_ENTRY):
                return line.strip().split(':', 1)[1]
