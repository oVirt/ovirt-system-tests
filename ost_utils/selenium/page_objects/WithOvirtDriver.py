#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
class WithOvirtDriver:
    def __init__(self, ovirt_driver):
        super(WithOvirtDriver, self).__init__()
        self.ovirt_driver = ovirt_driver
