#
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
import abc

import six


class EntityNotFoundError(Exception):
    pass


@six.add_metaclass(abc.ABCMeta)
class SDKEntity(object):

    _parent_service = None

    def __init__(self):
        self._id = None

    @property
    def id(self):
        return self._id

    @property
    def service(self):
        return self._service()

    @property
    def sdk_type(self):
        return self._service().get()

    @classmethod
    def register(cls, parent_service):
        cls._parent_service = parent_service

    def create(self, *args, **kwargs):
        sdk_type = self._build_sdk_type(*args, **kwargs)
        self._id = self._parent_service.add(sdk_type).id

    def import_by_name(self, name):
        entities = self._parent_service.list(search='name={}'.format(name))
        try:
            self._id = entities[0].id
        except IndexError:
            raise EntityNotFoundError(
                'entity "{}" was not found.'.format(name)
            )

    def remove(self):
        self._service().remove()

    @abc.abstractmethod
    def _build_sdk_type(self, *args, **kwargs):
        """
        This method is responsible for creating the SDK type that is
        added to the system via the parent service.
        """
        pass

    def _service(self):
        return self._parent_service.service(self._id)
