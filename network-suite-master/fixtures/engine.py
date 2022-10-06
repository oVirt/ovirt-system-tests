#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import os
import time

import pytest
from ovirtsdk4 import Connection

from ovirtlib import eventlib
from ovirtlib import joblib
from ovirtlib import sshlib
from ovirtlib import syncutil


@pytest.fixture(scope="session")
def engine_password():
    return "123"


@pytest.fixture(scope='session')
def api(
    ovirt_engine_service_up,
    engine_facts,
    engine_api_username,
    engine_password,
):
    return _create_engine_connection(
        engine_facts.default_ip(urlize=True),
        engine_api_username,
        engine_password,
    )


@pytest.fixture(scope='session', autouse=True)
def ovirt_engine_setup(deploy, engine_facts, engine_answer_file_path, ansible_engine):
    if os.environ.get('ENABLE_DEBUG_LOGGING'):
        debug = (
            'ORG_OVIRT_LOG_LEVEL="DEBUG"\\n'
            'KEYCLOAK_LOG_LEVEL="DEBUG"\\n'
            'CORE_BLL_LOG_LEVEL="DEBUG"\\n'
            'ROOT_LOG_LEVEL="DEBUG"'
        )
        ansible_engine.copy(content=debug, dest='/etc/ovirt-engine/engine.conf.d/98-logging.conf', mode='0644')
    ANSWER_FILE_TMP = '/root/engine-answer-file'

    engine = sshlib.Node(engine_facts.default_ip(), engine_facts.ssh_password)
    engine.sftp_put(engine_answer_file_path, ANSWER_FILE_TMP)

    commands = [
        f'engine-setup --offline --accept-defaults --config-append={ANSWER_FILE_TMP}',
        'engine-config --set ServerRebootTimeout=180',
        'systemctl restart ovirt-engine',
    ]
    for command in commands:
        engine.exec_command(command)
        time.sleep(1)


@pytest.fixture(scope='session', autouse=True)
def ovirt_engine_service_up(ovirt_engine_setup, engine_facts, engine_api_username, engine_password):
    syncutil.sync(
        exec_func=_create_engine_connection,
        exec_func_args=(
            engine_facts.default_ip(urlize=True),
            engine_api_username,
            engine_password,
        ),
        success_criteria=lambda api: isinstance(api, Connection),
        timeout=10 * 60,
    )
    yield


def _create_engine_connection(ip, engine_username, engine_password):
    url = 'https://{}/ovirt-engine/api'.format(ip)
    conn = Connection(
        url=url,
        username=engine_username,
        password=engine_password,
        insecure=True,
        debug=True,
    )
    if conn.test():
        return conn
    return None


@pytest.fixture(scope='function', autouse=True)
def test_invocation_logger(system, request, host_0_up, host_1_up):
    delim = '**************************************'
    events = eventlib.EngineEvents(system)
    test_invoke = f'{delim} OST - invoked: ' + str(request.node.nodeid)
    events.add(
        description=test_invoke,
        comment='delimiter for test function invocation in engine log',
    )
    sshlib.Node(host_0_up.address, host_0_up.root_password).exec_command(
        f'vdsm-client Host echo message="{test_invoke}"'
    )
    sshlib.Node(host_1_up.address, host_1_up.root_password).exec_command(
        f'vdsm-client Host echo message="{test_invoke}"'
    )
    events.add(description=f'OST - jobs: on test invocation: ' f'{joblib.AllJobs(system).describe_ill_fated()}')
