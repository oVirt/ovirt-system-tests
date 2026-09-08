#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import pytest

pytest.register_assert_rewrite('ost_utils')

# Register ost_utils.pytest hooks (pytest_addoption, pytest_collection_modifyitems,
# pytest_fixture_setup, ...). This must not be a plain import, otherwise linters
# would consider it unused and remove it (breaking --custom-repo etc).
pytest_plugins = ["ost_utils.pytest"]
