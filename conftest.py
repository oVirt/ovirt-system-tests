#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import pytest

pytest.register_assert_rewrite('ost_utils')

# Register the ost_utils pytest hooks and fixture modules as plugins.
# Fixtures defined (or re-exported) in these modules become available to all
# suites without needing re-export imports in the suite conftest.py files.
# Conftest-defined fixtures still override plugin fixtures of the same name.
pytest_plugins = [
    # hooks (pytest_addoption, pytest_collection_modifyitems, ...)
    "ost_utils.pytest",
    # hooks (pytest_runtest_logstart / _logfinish)
    "ost_utils.pytest.running_time",
    # shared session fixtures
    "ost_utils.pytest.fixtures.ansible",
    "ost_utils.pytest.fixtures.artifacts",
    "ost_utils.pytest.fixtures.backend",
    "ost_utils.pytest.fixtures.check_repos",
    "ost_utils.pytest.fixtures.defaults",
    "ost_utils.pytest.fixtures.deployment",
    "ost_utils.pytest.fixtures.engine",
    "ost_utils.pytest.fixtures.env",
    "ost_utils.pytest.fixtures",
    "ost_utils.pytest.fixtures.he",
    "ost_utils.pytest.fixtures.keycloak",
    "ost_utils.pytest.fixtures.network",
    "ost_utils.pytest.fixtures.node",
    "ost_utils.pytest.fixtures.sdk",
    "ost_utils.pytest.fixtures.selenium",
    "ost_utils.pytest.fixtures.storage",
    "ost_utils.pytest.fixtures.virt",
    "ost_utils.pytest.fixtures.vm",
]
