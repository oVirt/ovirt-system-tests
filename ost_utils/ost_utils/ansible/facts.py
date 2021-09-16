#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#


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
