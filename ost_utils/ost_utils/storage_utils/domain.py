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

from __future__ import absolute_import

import ovirtsdk4 as sdk4

from ost_utils import assertions
from ost_utils import engine_utils


def add(api, domain, dc_name):
    system_service = api.system_service()
    sds_service = system_service.storage_domains_service()
    with engine_utils.wait_for_event(system_service, 956): # USER_ADD_STORAGE_DOMAIN(956)
        sd = sds_service.add(domain)

        sd_service = sds_service.storage_domain_service(sd.id)
        assertions.assert_true_within_long(
            lambda: sd_service.get().status == sdk4.types.StorageDomainStatus.UNATTACHED
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
        attached_sd_service = attached_sds_service.storage_domain_service(sd.id)
        assertions.assert_true_within_long(
            lambda: attached_sd_service.get().status == sdk4.types.StorageDomainStatus.ACTIVE
        )
