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

import os


class Inventory(object):
    """A class to handle an ansible inventory directory"""

    def __init__(self, parent):
        """input:
        parent: A parent directory
        """
        self.dir = os.path.join(parent, "ansible_inventory")
        os.makedirs(self.dir, exist_ok=True)
        self.files = {}

    def add(self, name, contents):
        if name in self.files:
            raise RuntimeError(
                'ansible inventory: '
                f'Trying to overwrite an existing key {name}'
            )
        inv_file_name = f'{os.path.join(self.dir, name)}.yml'
        with open(inv_file_name, 'wb') as inv_file:
            inv_file.write(contents)
        self.files[name] = inv_file_name
