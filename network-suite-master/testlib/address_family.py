#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#


class AF(object):
    """
    Address family class
    """

    def __init__(self, version):
        self._version = version

    @property
    def version(self):
        return self._version

    @property
    def is6(self):
        return self._version == '6'

    @property
    def family(self):
        return 'inet' if self._version == '4' else 'inet6'
