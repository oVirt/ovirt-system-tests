#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import os

from ost_utils.memoized import memoized


@memoized
def inside_mock():
    return "MOCK_EXTERNAL_USER" in os.environ
