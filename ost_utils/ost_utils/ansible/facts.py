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

import threading

from ost_utils.ansible import module_mapper as mm


class FactNotFound(Exception):

    def __init__(self, fact):
        self.fact = fact

    def __str__(self):
        return f"Could not find fact: {self.fact}"


class Facts:
    """Uses ModuleMapper and gather_facts module to obtain and cache facts
    about a VM.

    For the rationale behind per-thread caching please see the docs on
    PrivateDir class.

    """

    def __init__(self, host_pattern):
        self._thread_local = threading.local()
        self._module_mapper = mm.module_mapper_for(host_pattern)

    @property
    def facts_gathered(self):
        return self._thread_local.__dict__.setdefault('facts_gathered', False)

    @facts_gathered.setter
    def facts_gathered(self, value):
        self._thread_local.facts_gathered = value

    def get(self, fact):
        if not self.facts_gathered:
            self.refresh()
        result = self._module_mapper.debug(var=fact)

        if result is not None:
            value = result.get(fact, None)
            if value == "VARIABLE IS NOT DEFINED!":
                raise FactNotFound(fact)
            if value is not None:
                return value

        raise FactNotFound(fact)

    def refresh(self):
        self._module_mapper.gather_facts()
        self.facts_gathered = True
