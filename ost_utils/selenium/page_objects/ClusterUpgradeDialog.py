#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By

from .Displayable import Displayable
from .EventsView import EventsView

LOGGER = logging.getLogger(__name__)


class ClusterUpgradeDialog(Displayable):
    def __init__(self, ovirt_driver):
        super(ClusterUpgradeDialog, self).__init__(ovirt_driver)

    def is_displayed(self):
        modal_text = self.ovirt_driver.find_element(
            ui_extension_modal_id='cluster-upgrade-modal',
            by=By.ID,
            value='cluster-upgrade-modal',
        ).text
        return 'Loading Cluster Data' not in modal_text

    def get_displayable_name(self):
        return 'Upgrade cluster'

    def toggle_check_all_hosts(self):
        check_all = self.ovirt_driver.find_element(
            ui_extension_modal_id='cluster-upgrade-modal',
            by=By.CSS_SELECTOR,
            value='input[name="check-all"]',
        )
        check_all.click()

    def toggle_check_for_upgrade(self):
        check_upgrade = self.ovirt_driver.find_element(
            ui_extension_modal_id='cluster-upgrade-modal',
            by=By.ID,
            value='upgrade-options-check-upgrade',
        )
        check_upgrade.click()

    def toggle_reboot_hosts(self):
        reboot_hosts = self.ovirt_driver.find_element(
            ui_extension_modal_id='cluster-upgrade-modal',
            by=By.ID,
            value='upgrade-options-reboot-after',
        )
        reboot_hosts.click()

    def next(self):
        modal_buttons = self.ovirt_driver.find_elements(
            ui_extension_modal_id='cluster-upgrade-modal',
            by=By.CSS_SELECTOR,
            value='footer>button.pf-m-primary',
        )
        next_button = next((b for b in modal_buttons if "Next" in b.text), None)
        assert next_button is not None
        next_button.click()

    def upgrade(self):
        modal_buttons = self.ovirt_driver.find_elements(
            ui_extension_modal_id='cluster-upgrade-modal',
            by=By.CSS_SELECTOR,
            value='footer>button.pf-m-primary',
        )
        upgrade_button = next((b for b in modal_buttons if "Upgrade" in b.text), None)
        assert upgrade_button is not None
        upgrade_button.click()

    def go_to_event_log(self):
        modal_buttons = self.ovirt_driver.find_elements(
            ui_extension_modal_id='cluster-upgrade-modal',
            by=By.CSS_SELECTOR,
            value='button',
        )
        goto_button = next((b for b in modal_buttons if "Go to Event Log" in b.text), None)
        assert goto_button is not None
        goto_button.click()

        events_view = EventsView(self.ovirt_driver)
        events_view.wait_for_displayed()
        return events_view
