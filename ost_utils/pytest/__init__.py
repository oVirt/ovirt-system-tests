#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import pytest


def pytest_addoption(parser):
    parser.addoption('--custom-repo', action='append')
    parser.addoption('--skip-custom-repos-check', action='store_true')


def pytest_collection_modifyitems(session, config, items):
    def get_item_module(item):
        return item.location[0]

    def get_item_ordering(item):
        mark = item.get_closest_marker('run')
        if not mark:
            raise RuntimeError(
                f"Some tests don't have ordering defined: {item}"
            )
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
