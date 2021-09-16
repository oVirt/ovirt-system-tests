#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import os
import re

from ost_utils.memoized import memoized


@memoized
def on_centos(ver=''):
    with open('/etc/redhat-release') as f:
        contents = f.readline()
        return re.match('(Red Hat|CentOS).*release {}'.format(ver), contents)


@memoized
def inside_mock():
    return "MOCK_EXTERNAL_USER" in os.environ
