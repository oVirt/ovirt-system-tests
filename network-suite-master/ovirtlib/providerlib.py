#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from contextlib import contextmanager

from ovirtsdk4 import types

from ovirtlib import syncutil
from ovirtlib.sdkentity import SDKRootEntity
from ovirtlib.sdkentity import SDKSubEntity
from ovirtlib.netlib import Network


class OpenStackImageProviders(SDKRootEntity):
    def create(self, name, url, requires_authentication):
        sdk_type = types.OpenStackImageProvider(
            name=name, url=url, requires_authentication=requires_authentication
        )
        self._create_sdk_entity(sdk_type)

    def is_provider_available(self, provider_name):
        providers_service = self.system.openstack_image_providers_service
        try:
            provider = next(
                provider
                for provider in providers_service.list()
                if provider.name == provider_name
            )
        except StopIteration:
            return False
        provider_service = providers_service.service(provider.id)
        return provider_service is not None

    def wait_until_available(self):
        syncutil.sync(
            exec_func=lambda: self.is_provider_available(
                self.get_sdk_type().name
            ),
            exec_func_args=(),
            success_criteria=lambda s: s,
        )

    def _get_parent_service(self, system):
        return system.openstack_image_providers_service


class OpenStackNetworkProvider(SDKRootEntity):
    def create(
        self,
        name,
        url,
        requires_authentication,
        username,
        password,
        authentication_url,
        tenant_name=None,
    ):
        sdk_type = types.OpenStackNetworkProvider(
            name=name,
            url=url,
            requires_authentication=requires_authentication,
            username=username,
            password=password,
            authentication_url=authentication_url,
            tenant_name=tenant_name,
        )
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, system):
        return system.openstack_network_providers_service

    @contextmanager
    def disable_auto_sync(self):
        orig_auto_sync = self.service.get().auto_sync
        self.service.update(types.OpenStackNetworkProvider(auto_sync=False))
        try:
            yield
        finally:
            if orig_auto_sync:
                self.service.update(
                    types.OpenStackNetworkProvider(auto_sync=orig_auto_sync)
                )


class OpenStackNetwork(SDKSubEntity):
    def create(self, name):
        sdk_type = types.OpenStackNetwork(name=name)
        self._create_sdk_entity(sdk_type)

    def _get_parent_service(self, openstack_network_provider):
        return openstack_network_provider.service.networks_service()

    def create_external_network(self, datacenter):
        self.service.import_(
            **{
                'async': False,
                'data_center': types.DataCenter(id=datacenter.id),
            }
        )

        ovirt_network = Network(datacenter)
        ovirt_network.import_by_name(self.get_sdk_type().name)
        return ovirt_network
