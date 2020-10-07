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
import os
import re

import pytest
from ovirtsdk4 import Connection

from ovirtlib import eventlib
from ovirtlib import syncutil
from testlib import suite


SUITE = os.path.split(os.environ['SUITE'])[1]
ANSWER_FILE_SRC = os.path.join(SUITE, 'engine-answer-file.conf')
ENGINE_DOMAIN = '-'.join(['lago', re.sub('\.', '-', SUITE), 'engine'])


@pytest.fixture(scope="session")
def engine_full_username():
    return "admin@internal"


@pytest.fixture(scope="session")
def engine_password():
    return "123"


@pytest.fixture(scope='session')
def api(engine, engine_full_username, engine_password):
    return _create_engine_connection(engine, engine_full_username,
                                     engine_password)


@pytest.fixture(scope='session', autouse=True)
def engine(fqdn, env, artifacts_path, engine_full_username, engine_password):
    with suite.collect_artifacts(env, artifacts_path, 'pre-tests'):
        engine = env.get_vms()[ENGINE_DOMAIN]

        ANSWER_FILE_TMP = '/tmp/answer-file'

        engine.copy_to(ANSWER_FILE_SRC, ANSWER_FILE_TMP)
        engine.ssh(
            [
                'engine-setup',
                '--config-append={}'.format(ANSWER_FILE_TMP),
                '--accept-defaults',
            ]
        )

        syncutil.sync(exec_func=_create_engine_connection,
                      exec_func_args=(engine, engine_full_username,
                                      engine_password),
                      success_criteria=lambda api: isinstance(api, Connection),
                      timeout=10*60)
        yield engine


def _create_engine_connection(engine, engine_full_username, engine_password):
    url = 'https://{}/ovirt-engine/api'.format(engine.ip())
    conn = Connection(
        url=url,
        username=engine_full_username,
        password=engine_password,
        insecure=True,
        debug=True,
    )
    if conn.test():
        return conn
    return None


def _exec_engine_config(engine, key, value):
    result = engine.ssh(
        [
            'engine-config',
            '--set',
            '{0}={1}'.format(key, value),
        ],
    )
    assert result.code == 0, (
        'setting {0}:{1} via engine-config failed with {2}'.format(
            key, value, result.code
        )
    )


@pytest.fixture(scope='function', autouse=True)
def test_invocation_logger(system, request):
    events = eventlib.EngineEvents(system)
    events.add(description='OST invoked: ' + str(request.node.nodeid),
               comment='delimiter for test function invocation in engine log')
