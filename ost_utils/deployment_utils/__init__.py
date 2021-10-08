#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import os


DEPLOYMENT_MARKER = "deployed"


def is_deployed(working_dir):
    return os.path.isfile(os.path.join(working_dir, DEPLOYMENT_MARKER))


def mark_as_deployed(working_dir):
    with open(os.path.join(working_dir, DEPLOYMENT_MARKER), "w") as _:
        pass
