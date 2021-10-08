#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
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
