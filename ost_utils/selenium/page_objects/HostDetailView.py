#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .EntityDetailView import EntityDetailView


class HostDetailView(EntityDetailView):
    def __init__(self, ovirt_driver, breadcrumbs, host_name):
        super(HostDetailView, self).__init__(ovirt_driver, breadcrumbs, host_name)

    def get_displayable_name(self):
        return 'Host detail view'

    def get_hostname(self):
        return self.ovirt_driver.find_element(By.ID, 'HostGeneralSubTabView_generalFormPanel_col0_row0_value').text
