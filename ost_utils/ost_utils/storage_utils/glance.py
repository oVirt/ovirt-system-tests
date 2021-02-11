#
# Copyright 2020 Red Hat, Inc.
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

import ovirtsdk4 as sdk4
import ovirtsdk4.types as types

from ost_utils import assertions


def add_domain(system_service, sd_name, url):
    target_server = sdk4.types.OpenStackImageProvider(
        name=sd_name,
        description=sd_name,
        url=url,
        requires_authentication=False
    )

    try:
        providers_service = system_service.openstack_image_providers_service()
        providers_service.add(target_server)
        glance = []

        def get():
            providers = [
                provider for provider in providers_service.list()
                if provider.name == sd_name
            ]
            if not providers:
                return False
            instance = providers_service.provider_service(providers.pop().id)
            if instance:
                glance.append(instance)
                return True
            else:
                return False

        assertions.assert_true_within_short(func=get, allowed_exceptions=[sdk4.NotFoundError])
    except (AssertionError, sdk4.NotFoundError):
        # RequestError if add method was failed.
        # AssertionError if add method succeed but we couldn't verify that glance was actually added
        return None

    return glance.pop()


def check_connectivity(system_service, sd_name):
    avail = False
    providers_service = system_service.openstack_image_providers_service()
    providers = [
        provider for provider in providers_service.list()
        if provider.name == sd_name
    ]
    if providers:
        glance = providers_service.provider_service(providers.pop().id)
        try:
            glance.test_connectivity()
            avail = True
        except sdk4.Error:
            pass

    return avail


def import_image(system_service, image_name, template_name, disk_name,
                 dest_storage_domain, dest_cluster, sd_name,
                 as_template=False):
    storage_domains_service = system_service.storage_domains_service()
    glance_storage_domain = storage_domains_service.list(search='name={}'.format(sd_name))[0]
    images = storage_domains_service.storage_domain_service(glance_storage_domain.id).images_service().list()
    image = [x for x in images if x.name == image_name][0]
    image_service = storage_domains_service.storage_domain_service(glance_storage_domain.id).images_service().image_service(image.id)
    result = image_service.import_(
        storage_domain=types.StorageDomain(
           name=dest_storage_domain,
        ),
        template=types.Template(
            name=template_name,
        ),
        cluster=types.Cluster(
           name=dest_cluster,
        ),
        import_as_template=as_template,
        disk=types.Disk(
            name=disk_name
        ),
    )
    disk = system_service.disks_service().list(search='name={}'.format(disk_name))[0]
    assert disk
