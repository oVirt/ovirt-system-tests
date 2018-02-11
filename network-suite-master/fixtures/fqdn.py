# Copyright 2018 Red Hat, Inc.
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
import errno
import shutil

import pytest

from fixtures.engine import ENGINE_DOMAIN
from fixtures.engine import ANSWER_FILE_SRC

HOSTS_FILE = '/etc/hosts'


class EngineNotResorvableError(Exception):
    pass


@pytest.fixture(scope='session')
def fqdn(env):
    BACKUP_FILE = HOSTS_FILE + 'OST-BACKUP'

    address = env.get_vms()[ENGINE_DOMAIN].ip()
    fqdn = _fetch_fqdn(ANSWER_FILE_SRC)

    remove_backup = False
    if not _fqdn_in_hosts_file(fqdn, address):
        try:
            shutil.copy2(HOSTS_FILE, BACKUP_FILE)
        except OSError as err:
            if err.errno == errno.EACCES:
                raise EngineNotResorvableError
            raise
        remove_backup = True
        _modify_hosts_file(fqdn, address)
    yield
    if remove_backup:
        shutil.move(BACKUP_FILE, HOSTS_FILE)


def _fqdn_in_hosts_file(fqdn, address):
    with open(HOSTS_FILE) as f:
        for line in f:
            line = line.split("#", 1)[0]
            args = line.split()
            if not args:
                continue
            addr = args[0]
            hostnames = args[1:]
            if addr == address and fqdn in hostnames:
                return True
    return False


def _fetch_fqdn(answer_file):
    FQDN_ENTRY = 'OVESETUP_CONFIG/fqdn'

    with open(answer_file) as f:
        for line in f:
            if line.startswith(FQDN_ENTRY):
                return line.strip().split(':', 1)[1]


def _modify_hosts_file(fqdn, address):
    TEMP_FILE = HOSTS_FILE + 'OST-TMP'
    TEMP_OST_ENTRY = '# temporary OST entry'
    ENGINE_ENTRY = ' '.join([address, fqdn, TEMP_OST_ENTRY]) + '\n'

    shutil.copy2(HOSTS_FILE, TEMP_FILE)
    with open(TEMP_FILE, 'r+') as tf:
        data = tf.read()
        tf.seek(0, 0)
        tf.write(ENGINE_ENTRY + data)

    shutil.move(TEMP_FILE, HOSTS_FILE)
