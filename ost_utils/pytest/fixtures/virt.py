#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import tempfile

import ovirtsdk4 as sdk4
import pytest

from ost_utils import versioning
from ost_utils import vmconsole
from ost_utils.shell import shell


@pytest.fixture(scope="session")
def cirros_image():
    return versioning.guest_os_image_name()


@pytest.fixture(scope="session")
def transformed_cirros_image():
    return versioning.transformed_guest_os_image_name()


@pytest.fixture(scope="session")
def cirros_image_glance_disk_name():
    return versioning.guest_os_glance_disk_name()


@pytest.fixture(scope="session")
def cirros_image_glance_template_name():
    return versioning.guest_os_template_name()


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
def rsa_pair():
    with tempfile.TemporaryDirectory(prefix='/tmp/') as tmpdir:
        key_path = f'{tmpdir}/id_rsa'
        shell(['ssh-keygen', '-t', 'rsa', '-f', f'{key_path}', '-N', ''])
        with open(f'{key_path}.pub') as f:
            public_key_content = f.read()
        yield public_key_content, key_path


@pytest.fixture(scope='session')
def cirros_serial_console(engine_ip, engine_admin_service, rsa_pair):
    engine_admin_service.ssh_public_keys_service().add(key=sdk4.types.SshPublicKey(content=rsa_pair[0]))
    serial = vmconsole.CirrosSerialConsole(
        rsa_pair[1],
        engine_ip,
    )
    yield serial
