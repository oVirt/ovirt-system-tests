#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By
from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class EntityDialog(Displayable):
    def __init__(
        self,
        ovirt_driver,
        entity_type,
        action,
    ):
        super(EntityDialog, self).__init__(ovirt_driver)
        self.action = action
        self.entity_type = entity_type

    def is_displayed(self):
        modal_title = self.ovirt_driver.find_element(By.CLASS_NAME, 'modal-title')
        spinner_displayed = self.ovirt_driver.is_class_name_present('spinner')
        return modal_title.text == f'{self.action} {self.entity_type}' and not spinner_displayed

    def get_displayable_name(self):
        return f'{self.action} {self.entity_type} dialog'

    def ok(self):
        LOGGER.debug(f'Click OK on {self.get_displayable_name()}')
        self.ovirt_driver.button_wait_and_click('OK')
        self.handle_ok_dialog_warnings()
        self.wait_for_not_displayed()

    def handle_ok_dialog_warnings(self):
        pass

    def cancel(self):
        LOGGER.debug(f'Click Cancel on {self.get_displayable_name()}')
        self.ovirt_driver.button_wait_and_click('Cancel')
        self.wait_for_not_displayed()
