#
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
from ovirtsdk4 import types

from lib import syncutil
from lib.sdkentity import SDKRootEntity


class OpenStackImageProviders(SDKRootEntity):

    def is_provider_available(self, provider_name):
        providers_service = \
            self._parent_sdk_system.openstack_image_providers_service
        try:
            provider = next(provider for provider in providers_service.list()
                            if provider.name == provider_name)
        except StopIteration:
            return False
        provider_service = providers_service.service(provider.id)
        return provider_service is not None

    def wait_until_available(self):
        syncutil.sync(
            exec_func=lambda: self.is_provider_available(self.sdk_type.name),
            exec_func_args=(),
            success_criteria=lambda s: s
        )

    def _get_parent_service(self, system):
        return system.openstack_image_providers_service

    def _build_sdk_type(self, name, url, requires_authentication):
        return types.OpenStackImageProvider(
            name=name,
            url=url,
            requires_authentication=requires_authentication
        )
