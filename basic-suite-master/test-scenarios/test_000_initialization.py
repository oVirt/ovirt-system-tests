#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

from ost_utils.shell import shell


def test_pull_ee_image(ansible_execution_environment):
    shell(
        [
            'podman',
            'pull',
            ansible_execution_environment,
        ]
    )
