#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import pytest

from fixtures import providers

from ovirtlib import storagelib
from ovirtlib import templatelib
from ovirtlib.sdkentity import EntityNotFoundError


@pytest.fixture(scope='session')
def cirros_template(
    system,
    ovirt_image_repo,
    default_cluster,
    default_storage_domain,
    cirros_image,
    transformed_cirros_image,
):
    cirros_template = transformed_cirros_image
    try:
        templatelib.get_template(system, cirros_template)
    except EntityNotFoundError:
        ovirt_image_sd = storagelib.StorageDomain(system)
        ovirt_image_sd.import_by_name(providers.OVIRT_IMAGE_REPO_NAME)

        default_storage_domain.import_image(
            default_cluster,
            ovirt_image_sd,
            cirros_image,
            template_name=cirros_template,
        )
        templatelib.wait_for_template_ok_status(system, cirros_template)

    return cirros_template
