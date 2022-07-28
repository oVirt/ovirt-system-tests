#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By
from .EntityDialog import EntityDialog

LOGGER = logging.getLogger(__name__)


class HostDialog(EntityDialog):
    def __init__(self, ovirt_driver, action):
        super(HostDialog, self).__init__(ovirt_driver, 'Host', action)

    def handle_ok_dialog_warnings(self):
        # Power management warning
        if self.ovirt_driver.is_id_present('DefaultConfirmationPopupView_OnSaveInternalNotFromApprove'):
            LOGGER.debug('Click OK on Power Management Configuration')
            self.ovirt_driver.xpath_click(
                '//div[@id="DefaultConfirmationPopupView_OnSaveInternalNotFromApprove"]/button'
            )
        else:
            LOGGER.debug('Power Management Configuration dialog is not present, continuing')

    def get_comment(self):
        return self.ovirt_driver.find_element(By.ID, 'HostPopupView_comment').get_attribute('value')

    def set_comment(self, comment):
        comment_field = self.ovirt_driver.find_element(By.ID, 'HostPopupView_comment')
        comment_field.clear()
        comment_field.send_keys(comment)
