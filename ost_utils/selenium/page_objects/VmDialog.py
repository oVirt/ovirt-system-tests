#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .EntityDialog import EntityDialog


class VmDialog(EntityDialog):
    def __init__(self, ovirt_driver, action):
        super(VmDialog, self).__init__(ovirt_driver, 'Virtual Machine', action)

    def is_displayed(self):
        cluster_element_text = self.ovirt_driver.find_element(By.ID, 'VmPopupWidget_dataCenterWithCluster').text
        return super().is_displayed() and cluster_element_text

    def setDescription(self, description):
        description_field = self.ovirt_driver.find_element(By.ID, 'VmPopupWidget_description')
        description_field.clear()
        description_field.send_keys(description)
