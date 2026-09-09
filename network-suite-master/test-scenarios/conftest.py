#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#

# Local suite fixtures are registered as pytest plugins via pytest_plugins in
# the root conftest.py, no re-export imports needed here.
pytest_plugins = [
    "fixtures.ansible",
    "fixtures.cluster",
    "fixtures.data_center",
    "fixtures.engine",
    "fixtures.fqdn",
    "fixtures.host",
    "fixtures.network",
    "fixtures.providers",
    "fixtures.storage",
    "fixtures.system",
    "fixtures.virt",
]
