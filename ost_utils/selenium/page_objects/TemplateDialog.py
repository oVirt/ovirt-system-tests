#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .EntityDialog import EntityDialog


class TemplateDialog(EntityDialog):
    def __init__(self, ovirt_driver, action):
        super(TemplateDialog, self).__init__(ovirt_driver, 'Template', action)

    def is_displayed(self):
        cluster_loaded = self.ovirt_driver.retry_if_known_issue(self._is_cluster_loaded)
        return super().is_displayed() and cluster_loaded

    def _is_cluster_loaded(self):
        cluster_element = self.ovirt_driver.find_element(By.ID, 'TemplateEditPopupWidget_dataCenterWithCluster')
        return not cluster_element.is_displayed() or cluster_element.text

    def setDescription(self, description):
        description_field = self.ovirt_driver.find_element(By.ID, 'TemplateEditPopupWidget_description')
        description_field.clear()
        description_field.send_keys(description)
