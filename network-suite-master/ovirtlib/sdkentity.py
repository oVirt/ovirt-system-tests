#
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
import abc

import six

import ovirtsdk4


class EntityAlreadyInitialized(Exception):
    pass


class EntityNotFoundError(Exception):
    pass


class EntityCreationError(Exception):
    pass


@six.add_metaclass(abc.ABCMeta)
class SDKEntity(object):

    def __init__(self):
        self._service = None
        self._parent_service = None

    @property
    def id(self):
        return self._service.get().id

    @property
    def service(self):
        return self._service

    def get_sdk_type(self):
        return self._service.get()

    @abc.abstractmethod
    def create(self, *args, **kwargs):
        """This method is responsible for creating and
        adding the entity to the system
        """
        pass

    def import_by_name(self, name):
        entities = (entity for entity in self._parent_service.list()
                    if entity.name == name)
        try:
            entity_id = next(entities).id
        except StopIteration:
            raise EntityNotFoundError(
                'entity "{}" was not found.'.format(name)
            )
        service = self._parent_service.service(entity_id)
        self._set_service(service)

    def import_by_id(self, entity_id):
        service = self._parent_service.service(entity_id)
        self._set_service(service)

    def remove(self):
        self._service.remove()

    def update(self, **kwargs):
        sdk_type = self.get_sdk_type()
        for key, value in six.viewitems(kwargs):
            setattr(sdk_type, key, value)
        self._service.update(sdk_type)

    def _create_sdk_entity(self, sdk_type):
        try:
            entity_id = self._parent_service.add(sdk_type).id
        except ovirtsdk4.Error as err:
            raise EntityCreationError(err.args[0])
        service = self._parent_service.service(entity_id)
        self._set_service(service)

    def _set_service(self, service):
        if self._service is not None:
            raise EntityAlreadyInitialized
        self._service = service


@six.add_metaclass(abc.ABCMeta)
class SDKRootEntity(SDKEntity):

    def __init__(self, parent_sdk_system):
        super(SDKRootEntity, self).__init__()
        self._parent_sdk_system = parent_sdk_system
        self._parent_service = self._get_parent_service(parent_sdk_system)

    @abc.abstractmethod
    def _get_parent_service(self, sdk_system):
        """
        This method is responsible for getting the parent service given
        SDKSystem.
        """
        pass


@six.add_metaclass(abc.ABCMeta)
class SDKSubEntity(SDKEntity):

    def __init__(self, parent_sdk_entity):
        super(SDKSubEntity, self).__init__()
        self._parent_sdk_entity = parent_sdk_entity
        self._parent_service = self._get_parent_service(parent_sdk_entity)

    @abc.abstractmethod
    def _get_parent_service(self, parent_entity):
        """
        This method is responsible for getting the parent service given
        the parent SDKEntity.
        """
        pass
