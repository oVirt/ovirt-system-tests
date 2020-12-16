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

"""Backend-specific information

This is the only module that should contain backend-specific
information. Every other part of OST code should be backend-agnostic.

ATM we only support lago, but the code below should be adjusted
if new backends are available.

"""

import os

from ost_utils.backend import lago
from ost_utils import memoized


@memoized.memoized
def default_backend():
    return lago.LagoBackend(os.environ["PREFIX"])
