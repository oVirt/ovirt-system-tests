#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import ovirtsdk4 as sdk4

from ost_utils import assert_utils
from ost_utils import engine_utils


def add(api, domain, dc_name):
    system_service = api.system_service()
    sds_service = system_service.storage_domains_service()
    with engine_utils.wait_for_event(
        system_service, 956
    ):  # USER_ADD_STORAGE_DOMAIN(956)
        sd = sds_service.add(domain)

        sd_service = sds_service.storage_domain_service(sd.id)
        assert assert_utils.equals_within_long(
            lambda: sd_service.get().status,
            sdk4.types.StorageDomainStatus.UNATTACHED,
        )

    data_centers = system_service.data_centers_service()
    dc = data_centers.list(search='name={}'.format(dc_name))[0]
    dc_service = data_centers.data_center_service(dc.id)
    attached_sds_service = dc_service.storage_domains_service()

    with engine_utils.wait_for_event(system_service, [966, 962]):
        # USER_ACTIVATED_STORAGE_DOMAIN(966)
        # USER_ATTACH_STORAGE_DOMAIN_TO_POOL(962)
        attached_sds_service.add(
            sdk4.types.StorageDomain(
                id=sd.id,
            ),
        )
        attached_sd_service = attached_sds_service.storage_domain_service(
            sd.id
        )
        assert assert_utils.equals_within_long(
            lambda: attached_sd_service.get().status,
            sdk4.types.StorageDomainStatus.ACTIVE,
        )
