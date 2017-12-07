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
import os

import pytest

from lago import sdk as lagosdk
from ovirtsdk4 import Connection

from lib import syncutil
from lib.netlib import Network


ENGINE_DOMAIN = 'lago-network-suite-master-engine'


def pytest_addoption(parser):
    parser.addoption(
        '--lago-env',
        action='store',
        default='.lago',
        help='path to lago workdir'
    )


@pytest.fixture(scope='session')
def env():
    workdir = pytest.config.getoption('--lago-env')
    lago_env = lagosdk.load_env(workdir=workdir)

    lago_env.start()
    yield lago_env
    lago_env.destroy()


@pytest.fixture(scope='session', autouse=True)
def engine(env):
    engine = env.get_vms()[ENGINE_DOMAIN]

    ANSWER_FILE_TMP = '/tmp/answer-file'
    ANSWER_FILE_SRC = os.path.join(
        os.environ.get('SUITE'), 'engine-answer-file.conf'
    )
    engine.copy_to(ANSWER_FILE_SRC, ANSWER_FILE_TMP)
    engine.ssh(
        [
            'OTOPI_DEBUG=1',
            'engine-setup',
            '--config-append={}'.format(ANSWER_FILE_TMP),
            '--accept-defaults',
        ]
    )

    syncutil.sync(exec_func=_get_engine_api,
                  exec_func_args=(engine,),
                  success_criteria=lambda api: isinstance(api, Connection))
    return engine


@pytest.fixture(scope='session')
def api(engine):
    return _get_engine_api(engine)


def _get_engine_api(engine):
    try:
        return engine.get_api_v4()
    except:
        return None


@pytest.fixture(scope='session')
def system_service(api):
    return api.system_service()


@pytest.fixture(scope='session')
def _networks_service(system_service):
    service = system_service.networks_service()
    Network.register(service)
    return service


@pytest.fixture(scope='session', autouse=True)
def ovirtmgmt_network(_networks_service):
    network = Network()
    network.import_by_name('ovirtmgmt')
    return network
