#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import abc

import ovirtsdk4


class EntityAlreadyInitialized(Exception):
    pass


class EntityNotFoundError(Exception):
    pass


class EntityCreationError(Exception):
    pass


class SDKEntity(metaclass=abc.ABCMeta):
    def __init__(self):
        self._service = None
        self._parent_service = None
        self._parent_sdk_system = None

    @property
    def id(self):
        return self._service.get().id

    @property
    def service(self):
        return self._service

    @property
    def system(self):
        return self._parent_sdk_system

    def get_sdk_type(self):
        return self._service.get()

    def create(self, *args, **kwargs):
        """This method is responsible for creating and
        adding the entity to the system
        """
        raise NotImplementedError('not implemented yet')

    def import_by_name(self, name):
        entities = (entity for entity in self._parent_service.list() if entity.name == name)
        try:
            entity_id = next(entities).id
        except StopIteration:
            raise EntityNotFoundError(f'entity "{name}" was not found.')
        service = self._parent_service.service(entity_id)
        self._set_service(service)

    def import_by_id(self, entity_id):
        service = self._parent_service.service(entity_id)
        self._set_service(service)

    def remove(self):
        self._service.remove()

    def update(self, **kwargs):
        sdk_type = self.get_sdk_type()
        for key, value in kwargs.items():
            setattr(sdk_type, key, value)
        return self._service.update(sdk_type)

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

    def _execute_without_raising(self, func):
        try:
            return func()
        except Exception as e:
            return f'<{self.__class__.__name__}, ' f'{func.__name__} failed with: {str(e)}>'


class SDKRootEntity(SDKEntity, metaclass=abc.ABCMeta):
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


class SDKSubEntity(SDKEntity, metaclass=abc.ABCMeta):
    def __init__(self, parent_sdk_entity):
        super(SDKSubEntity, self).__init__()
        self._parent_sdk_system = parent_sdk_entity.system
        self._parent_sdk_entity = parent_sdk_entity
        self._parent_service = self._get_parent_service(parent_sdk_entity)

    @abc.abstractmethod
    def _get_parent_service(self, parent_entity):
        """
        This method is responsible for getting the parent service given
        the parent SDKEntity.
        """
        pass
