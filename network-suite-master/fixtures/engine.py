# Copyright 2017-2018 Red Hat, Inc.
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

from lib import syncutil
from testlib import suite


SUITE = os.path.split(os.environ['SUITE'])[1]
ANSWER_FILE_SRC = os.path.join(SUITE, 'engine-answer-file.conf')
ENGINE_DOMAIN = '-'.join(['lago', re.sub('\.', '-', SUITE), 'engine'])


@pytest.fixture(scope='session')
def api(engine):
    return _get_engine_api(engine)


@pytest.fixture(scope='session', autouse=True)
def engine(fqdn, env, artifacts_path):
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
        syncutil.sync(exec_func=_get_engine_api,
                      exec_func_args=(engine,),
                      success_criteria=lambda api: isinstance(api, Connection))
        return engine


def _get_engine_api(engine):
    try:
        return engine.get_api_v4()
    except Exception:
        return None
