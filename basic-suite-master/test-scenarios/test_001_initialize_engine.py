#
# Copyright 2014 Red Hat, Inc.
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
from __future__ import absolute_import

import os
import socket

from tempfile import NamedTemporaryFile

from ost_utils.pytest.fixtures.ansible import *
from ost_utils.pytest.fixtures.engine import *


# workaround for https://issues.redhat.com/browse/RHV-39904
def test_set_hostnames(ansible_by_hostname, all_hostnames):
    for hostname in all_hostnames:
        ansible_by_hostname(hostname).hostname(name=hostname)


def test_check_ansible_connectivity(ansible_engine, ansible_hosts):
    ansible_engine.ping()
    ansible_hosts.ping()


def test_initialize_engine(suite_dir, engine_ip, ansible_engine):
    answer_file_src = os.path.join(suite_dir, 'engine-answer-file.conf')

    ansible_engine.copy(
        src=answer_file_src,
        dest='/tmp/answer-file',
    )

    host_name = socket.getfqdn()
    host_ip = socket.gethostbyname(host_name)

    with NamedTemporaryFile(mode='w') as sso_conf:
        sso_conf.write(
            (
                'SSO_ALTERNATE_ENGINE_FQDNS='
                '"${{SSO_ALTERNATE_ENGINE_FQDNS}} {0} {1} {2}"\n'
            ).format(engine_ip, host_name, host_ip)
        )
        sso_conf.flush()
        os.fsync(sso_conf.fileno())
        ansible_engine.copy(
            src=sso_conf.name,
            dest='/etc/ovirt-engine/engine.conf.d/99-custom-fqdn.conf',
            mode='0644'
        )

    if os.environ.get('ENABLE_DEBUG_LOGGING'):
        ansible_engine.shell(
            'sed -i '
            '-e "/.*logger category=\\"org.ovirt\\"/{ n; s/INFO/DEBUG/ }" '
            '-e "/.*logger category=\\"org.ovirt.engine.core.bll\\"/{ n; s/INFO/DEBUG/ }" '
            '-e "/.*<root-logger>/{ n; s/INFO/DEBUG/ }" '
            '/usr/share/ovirt-engine/services/ovirt-engine/ovirt-engine.xml.in'
        )

    ansible_engine.shell(
        'engine-setup '
        '--config-append=/tmp/answer-file '
        '--accept-defaults '
        '--offline '
    )
    ansible_engine.shell('ss -anp')

    ansible_engine.systemd(name='ovirt-engine-notifier', state='started')
    ansible_engine.systemd(name='ovirt-engine', state='started')
    ansible_engine.systemd(name='ovirt-engine-dwhd', state='started')


def test_engine_config(ansible_engine, engine_restart):
    ansible_engine.shell("engine-config --set VdsLocalDisksLowFreeSpace=400")
    ansible_engine.shell("engine-config --set OvfUpdateIntervalInMinutes=10")
    ansible_engine.shell("engine-config --set ServerRebootTimeout=120")
    ansible_engine.shell(
        "engine-config --set IsIncrementalBackupSupported=True --cver=4.4")

    engine_restart()
