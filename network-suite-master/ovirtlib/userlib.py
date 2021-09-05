#
# Copyright 2017-2021 Red Hat, Inc.
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
from contextlib import contextmanager

import logging

from ovirtsdk4 import types

from ovirtlib.sdkentity import SDKRootEntity

LOGGER = logging.getLogger(__name__)


class User(SDKRootEntity):
    def __init__(self, parent_sdk_system):
        super(User, self).__init__(parent_sdk_system)
        self._user = None

    @property
    def name(self):
        return self.get_sdk_type().name

    def create(self, *args, **kwargs):
        raise NotImplementedError('not implemented yet')

    def list_keys(self):
        return self.service.ssh_public_keys_service().list()

    def add_public_key(self, ssh_public_key):
        return self.service.ssh_public_keys_service().add(
            key=types.SshPublicKey(content=ssh_public_key)
        )

    def remove_public_key(self, id):
        return self.service.ssh_public_keys_service().key_service(id).remove()

    @contextmanager
    def toggle_public_key(self, ssh_public_key):
        key = None
        try:
            LOGGER.debug(f'adding public key to {self.name}')
            key = self.add_public_key(ssh_public_key)
            yield key.id
        finally:
            if key:
                self.remove_public_key(key.id)
            else:
                LOGGER.debug(f'failed adding public key to {self.name}')

    def _get_parent_service(self, system):
        return system.users_service

    def __repr__(self):
        return self._execute_without_raising(
            lambda: (
                f'<{self.__class__.__name__}| '
                f'name:{self.name}, '
                f'has_keys:{bool(self.list_keys())}, '
                f'id:{self.id}>'
            )
        )
