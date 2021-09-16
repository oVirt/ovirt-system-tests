#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import collections


_CommandStatus = collections.namedtuple(
    'CommandStatus', ('out', 'err', 'code')
)


class CommandStatus(_CommandStatus):
    def __nonzero__(self):
        return self.code
