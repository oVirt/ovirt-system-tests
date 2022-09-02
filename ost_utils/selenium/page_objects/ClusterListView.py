#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By
from .ClusterDetailView import ClusterDetailView
from .ClusterDialog import ClusterDialog
from .Displayable import Displayable
from .EntityListView import EntityListView
from .EventsView import EventsView

LOGGER = logging.getLogger(__name__)


class ClusterListView(EntityListView):
    def __init__(self, ovirt_driver):
        super(ClusterListView, self).__init__(
            ovirt_driver,
            'cluster',
            ['Compute', 'Clusters'],
            'MainClusterView_table_content_col1_row',
        )

    def open_detail_view(self, name):
        super().open_detail_view(name)

        detail_view = ClusterDetailView(self.ovirt_driver, self.breadcrumbs, name)
        detail_view.wait_for_displayed()
        return detail_view

    def edit(self, name):
        super().edit(name)

        dialog = ClusterDialog(self.ovirt_driver, 'Edit')
        dialog.wait_for_displayed()
        return dialog

    def is_new_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Edit')

    def is_upgrade_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Upgrade')

    def upgrade(self, cluster_name):
        LOGGER.debug('Upgrade cluster')
        self.ovirt_driver.xpath_click('//button[text()="Upgrade"]')

        upgrade_dialog = ClusterUpgradeDialog(self.ovirt_driver)
        upgrade_dialog.wait_for_displayed()
        return upgrade_dialog


class ClusterUpgradeDialog(Displayable):
    def __init__(self, ovirt_driver):
        super(ClusterUpgradeDialog, self).__init__(ovirt_driver)

    def is_displayed(self):
        modal_text = self.ovirt_driver.find_element(By.ID, 'cluster-upgrade-modal').text
        return 'Loading Cluster Data' not in modal_text

    def get_displayable_name(self):
        return 'Upgrade cluster'

    def toggle_check_all_hosts(self):
        self.ovirt_driver.xpath_wait_and_click('Select all hosts is not clickable', '//input[@name="check-all"]')

    def toggle_check_for_upgrade(self):
        self.ovirt_driver.xpath_wait_and_click(
            'Check for upgrade is not clickable', '//input[@id="upgrade-options-check-upgrade"]'
        )

    def toggle_reboot_hosts(self):
        self.ovirt_driver.xpath_wait_and_click(
            'Reboot hosts is not clickable', '//input[@id="upgrade-options-reboot-after"]'
        )

    def next(self):
        self.ovirt_driver.xpath_wait_and_click('Next is not clickable', '//button[text()="Next"]')

    def upgrade(self):
        self.ovirt_driver.xpath_wait_and_click('Upgrade is not clickable', '//footer/button[text()="Upgrade"]')

    def go_to_event_log(self):
        self.ovirt_driver.xpath_wait_and_click('Go to events is not clickable', '//button[text()="Go to Event Log"]')

        events_view = EventsView(self.ovirt_driver)
        events_view.wait_for_displayed()
        return events_view
