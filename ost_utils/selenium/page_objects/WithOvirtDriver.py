#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from ost_utils.selenium.navigation.driver import Driver


class WithOvirtDriver:
    def __init__(self, ovirt_driver: Driver):
        super(WithOvirtDriver, self).__init__()
        self.ovirt_driver = ovirt_driver
