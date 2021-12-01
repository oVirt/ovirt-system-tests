#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

from functools import cache
import os


@cache
def inside_mock():
    return "MOCK_EXTERNAL_USER" in os.environ
