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

import pytest


def pytest_collection_modifyitems(session, config, items):

    def get_item_module(item):
        return item.location[0]

    def get_item_ordering(item):
        mark = item.get_closest_marker('run')
        if not mark:
            raise RuntimeError("Some tests don't have ordering defined")
        return mark.kwargs.get('order')

    def module_uses_item_ordering(module_items):
        return any(item.get_closest_marker('run') for item in module_items)

    items_by_module = {}

    for item in items:
        items_by_module.setdefault(get_item_module(item), []).append(item)

    items[:] = []

    for module in sorted(items_by_module.keys()):
        module_items = items_by_module[module]
        if module_uses_item_ordering(module_items):
            module_items = sorted(module_items, key=get_item_ordering)
        items.extend(module_items)


def order_by(test_list):

    def wrapper(test_fn):
        try:
            idx = test_list.index(test_fn.__name__)
            return pytest.mark.run(order=idx)(test_fn)
        except ValueError:
            return pytest.mark.skip(reason="Not found in test list")(test_fn)

    return wrapper
