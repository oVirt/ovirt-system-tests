#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import random

import ovirtsdk4

from ovirtlib.sdkentity import SDKRootEntity


class EngineEvents(SDKRootEntity):
    def _get_parent_service(self, sdk_system):
        return sdk_system.events_service

    def create(self):
        raise NotImplementedError('oVirt cannot create Engine Events')

    def add(self, description, comment='', origin='OST-network-suite'):
        self._parent_service.add(
            ovirtsdk4.types.Event(
                comment=comment,
                custom_id=random.randrange(1, 2 ** 31),
                description=description,
                origin=origin,
                severity=ovirtsdk4.types.LogSeverity(
                    ovirtsdk4.types.LogSeverity.NORMAL
                ),
            )
        )
