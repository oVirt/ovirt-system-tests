#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import ovirtsdk4 as sdk4

from ost_utils import assert_utils


def add_domain(system_service, sd_name, url):
    target_server = sdk4.types.OpenStackImageProvider(
        name=sd_name,
        description=sd_name,
        url=url,
        requires_authentication=False,
    )

    try:
        providers_service = system_service.openstack_image_providers_service()
        providers_service.add(target_server)
        glance = []

        def get():
            providers = [provider for provider in providers_service.list() if provider.name == sd_name]
            if not providers:
                return False
            instance = providers_service.provider_service(providers.pop().id)
            if instance:
                glance.append(instance)
                return True
            else:
                return False

        assert assert_utils.true_within_short(func=get, allowed_exceptions=[sdk4.NotFoundError])
    except (AssertionError, sdk4.NotFoundError):
        # RequestError if add method was failed.
        # AssertionError if add method succeed but we couldn't verify that
        # glance was actually added
        return None

    return glance.pop()


def check_connectivity(system_service, sd_name):
    avail = False
    providers_service = system_service.openstack_image_providers_service()
    providers = [provider for provider in providers_service.list() if provider.name == sd_name]
    if providers:
        glance = providers_service.provider_service(providers.pop().id)
        try:
            glance.test_connectivity()
            avail = True
        except sdk4.Error:
            pass

    return avail
