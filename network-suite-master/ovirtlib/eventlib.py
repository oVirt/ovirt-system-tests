#
# Copyright 2019 Red Hat, Inc.
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
import random

import ovirtsdk4

from ovirtlib.sdkentity import SDKRootEntity


class EngineEvents(SDKRootEntity):

    def _get_parent_service(self, sdk_system):
        return sdk_system.events_service

    def create(self):
        raise NotImplementedError('oVirt cannot create Engine Events')

    def add(self, description, comment='', origin='OST-network-suite'):
        self._parent_service.add(ovirtsdk4.types.Event(
            comment=comment,
            custom_id=random.randrange(1, 2**31),
            description=description,
            origin=origin,
            severity=ovirtsdk4.types.LogSeverity(
                ovirtsdk4.types.LogSeverity.NORMAL
            )
        ))
