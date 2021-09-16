#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

from ost_utils.shell import shell


def test_pull_ee_image():
    shell(
        [
            'podman',
            'pull',
            'quay.io/ovirt/el8stream-ansible-executor:latest',
        ]
    )
