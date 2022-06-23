#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import tempfile

import ovirtsdk4 as sdk4
import pytest

from ost_utils import vmconsole
from ost_utils.shell import shell


@pytest.fixture(scope="session")
def cirros_image_disk_name():
    return 'cirros_disk'


@pytest.fixture(scope="session")
def cirros_image_template_name():
    return 'cirros_template'


@pytest.fixture(scope="session")
def cirros_image_template_version_name():
    return 'cirros_template_v2'


@pytest.fixture(scope='session')
def rsa_pair(engine_admin_service):
    with tempfile.TemporaryDirectory(prefix='/tmp/') as tmpdir:
        key_path = f'{tmpdir}/id_rsa'
        shell(['ssh-keygen', '-t', 'rsa', '-f', f'{key_path}', '-N', ''])
        with open(f'{key_path}.pub') as f:
            public_key_content = f.read()
        engine_admin_service.ssh_public_keys_service().add(key=sdk4.types.SshPublicKey(content=public_key_content))
        yield public_key_content, key_path


@pytest.fixture(scope='session')
def cirros_serial_console(engine_ip, rsa_pair):
    serial = vmconsole.CirrosSerialConsole(
        rsa_pair[1],
        engine_ip,
    )
    yield serial
