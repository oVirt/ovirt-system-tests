#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .EntityDialog import EntityDialog


class ClusterDialog(EntityDialog):
    def __init__(self, ovirt_driver, action):
        super(ClusterDialog, self).__init__(ovirt_driver, 'Cluster', action)

    def is_displayed(self):
        cpu_loaded = self.ovirt_driver.retry_if_known_issue(self._is_cpu_loaded)
        return super().is_displayed() and cpu_loaded

    def _is_cpu_loaded(self):
        cpu_element = self.ovirt_driver.find_element(By.ID, 'ClusterPopupView_cpuEditor')
        return cpu_element.text.strip()

    def setDescription(self, description):
        description_field = self.ovirt_driver.find_element(By.ID, 'ClusterPopupView_descriptionEditor')
        description_field.clear()
        description_field.send_keys(description)
