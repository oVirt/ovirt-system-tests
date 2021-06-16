#
# Copyright 2020-2021 Red Hat, Inc.
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


class FactNotFound(Exception):

    def __init__(self, fact):
        self.fact = fact

    def __str__(self):
        return f"Could not find fact: {self.fact}"


class Facts:
    """
    Uses ModuleMapper and gather_facts module to obtain and cache facts
    about a VM.
    """

    def __init__(self, module_mapper):
        self._module_mapper = module_mapper
        self._cache = {}

    def get_all(self):
        if not self._cache:
            self.refresh()
        return self._cache

    def get(self, key):
        """
        :param str key: key in the outermost level of the facts dict.
         to get a leaf value in the facts dict use -
         self.get('ansible_eth0').get('ipv4').get('address')
        """
        if not self._cache:
            self.refresh()
        return self._cache[key]

    def refresh(self):
        self._cache = self._module_mapper.gather_facts()['ansible_facts']
