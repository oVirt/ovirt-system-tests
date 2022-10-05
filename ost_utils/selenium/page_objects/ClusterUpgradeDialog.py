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
        dialog = self.ovirt_driver.find_dialog_root('cluster-upgrade-modal', True)
        modal_text = dialog.find_element(By.ID, 'cluster-upgrade-modal').text
        return 'Loading Cluster Data' not in modal_text

    def get_displayable_name(self):
        return 'Upgrade cluster'

    def toggle_check_all_hosts(self):
        check_all = self.ovirt_driver.find_dialog_element(
            'cluster-upgrade-modal',
            message='Select all hosts is not clickable',
            locator=(By.CSS_SELECTOR, 'input[name="check-all"]'),
            waitCondition=lambda el: el.is_displayed() and el.is_enabled(),
        )
        check_all.click()

    def toggle_check_for_upgrade(self):
        check_upgrade = self.ovirt_driver.find_dialog_element(
            'cluster-upgrade-modal',
            message='Check for upgrade is not clickable',
            locator=(By.ID, 'upgrade-options-check-upgrade'),
            waitCondition=lambda el: el.is_displayed() and el.is_enabled(),
        )
        check_upgrade.click()

    def toggle_reboot_hosts(self):
        reboot_hosts = self.ovirt_driver.find_dialog_element(
            'cluster-upgrade-modal',
            message='Reboot hosts is not clickable',
            locator=(By.ID, 'upgrade-options-reboot-after'),
            waitCondition=lambda el: el.is_displayed() and el.is_enabled(),
        )
        reboot_hosts.click()

    def next(self):
        dialog = self.ovirt_driver.find_dialog_root('cluster-upgrade-modal')
        next_button = next(
            (b for b in dialog.find_elements(By.CSS_SELECTOR, 'footer>button.pf-m-primary') if "Next" in b.text), None
        )
        assert next_button is not None
        next_button.click()

    def upgrade(self):
        dialog = self.ovirt_driver.find_dialog_root('cluster-upgrade-modal')
        upgrade_button = next(
            (b for b in dialog.find_elements(By.CSS_SELECTOR, 'footer>button.pf-m-primary') if "Upgrade" in b.text),
            None,
        )
        assert upgrade_button is not None
        upgrade_button.click()

    def go_to_event_log(self):
        dialog = self.ovirt_driver.find_dialog_root('cluster-upgrade-modal')
        goto_button = next(
            (b for b in dialog.find_elements(By.CSS_SELECTOR, 'button') if "Go to Event Log" in b.text), None
        )
        assert goto_button is not None
        goto_button.click()

        events_view = EventsView(self.ovirt_driver)
        events_view.wait_for_displayed()
        return events_view
