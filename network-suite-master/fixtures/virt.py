# Copyright 2018-2021 Red Hat, Inc.
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
from collections import namedtuple

import contextlib
import logging
import os
import random
import pytest

from fixtures import providers

from ovirtlib import storagelib
from ovirtlib import templatelib
from ovirtlib import virtlib
from ovirtlib.sdkentity import EntityNotFoundError

from ost_utils import shell

LOGGER = logging.getLogger(__name__)
Rsa = namedtuple('Rsa', ['public_key_content', 'private_key_path'])


@pytest.fixture(scope='session')
def cirros_template(system, ovirt_image_repo, default_cluster,
                    default_storage_domain, cirros_image,
                    transformed_cirros_image):
    cirros_template = transformed_cirros_image
    try:
        templatelib.get_template(system, cirros_template)
    except EntityNotFoundError:
        ovirt_image_sd = storagelib.StorageDomain(system)
        ovirt_image_sd.import_by_name(providers.OVIRT_IMAGE_REPO_NAME)

        default_storage_domain.import_image(
            default_cluster, ovirt_image_sd, cirros_image,
            template_name=cirros_template
        )
        templatelib.wait_for_template_ok_status(system, cirros_template)

    return cirros_template


@pytest.fixture(scope='session')
def vmconsole_rsa():
    private_key_path = f'/tmp/vmconsole_rsa_{random.randrange(1, 2**31)}'
    with contextlib.suppress(FileNotFoundError):
        os.remove(f'{private_key_path}')
        os.remove(f'{private_key_path}.pub')
    shell.shell([
        'ssh-keygen', '-t', 'rsa', '-f', f'{private_key_path}', '-N', ''
    ])
    with open(f'{private_key_path}.pub') as f:
        public_key_content = f.read()
        LOGGER.debug(f'read vmconsole public key {public_key_content}')
    return Rsa(public_key_content=public_key_content,
               private_key_path=f'{private_key_path}')


@pytest.fixture(scope='function')
def serial_console(engine_facts, engine_admin, vmconsole_rsa):
    with engine_admin.toggle_public_key(vmconsole_rsa.public_key_content):
        serial = virtlib.CirrosSerialConsole(
            vmconsole_rsa.private_key_path,
            engine_facts.default_ip(),
        )
        yield serial
