#
# Copyright 2021 Red Hat, Inc.
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
import logging

LOGGER = logging.getLogger(__name__)


class AF(object):
    """
    Address family class
    """
    def __init__(self, version):
        if version not in ['4', '6']:
            LOGGER.warning(f'suite invoked with unsupported version {version}.'
                           f'using version 4')
            version = '4'
        self._version = version

    @property
    def version(self):
        return self._version

    @property
    def is6(self):
        return self._version == '6'

    @property
    def family(self):
        return 'inet' if self._version == '4' else 'inet6'
