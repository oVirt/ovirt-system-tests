#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs
from .WithNotifications import WithNotifications


class DashboardView(Displayable, WithBreadcrumbs, WithNotifications):

    DASHBOARD_IFRAME_SELECTOR = (
        '//iframe[@src="plugin/ui-extensions/dashboard.html"]'
    )

    def __init__(self, ovirt_driver):
        super(DashboardView, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self._execute_in_frame(self._is_displayed)

    def get_displayable_name(self):
        return 'Dashboard view'

    def data_centers_count(self):
        return self._execute_in_frame(
            self._get_aggregate_count, 'Data Centers'
        )

    def clusters_count(self):
        return self._execute_in_frame(self._get_aggregate_count, 'Clusters')

    def hosts_count(self):
        return self._execute_in_frame(self._get_aggregate_count, 'Hosts')

    def storage_domains_count(self):
        return self._execute_in_frame(
            self._get_aggregate_count, 'Data Storage Domains'
        )

    def vm_count(self):
        return self._execute_in_frame(
            self._get_aggregate_count, 'Virtual Machines'
        )

    def events_count(self):
        return self._execute_in_frame(self._get_aggregate_count, 'Events')

    def _execute_in_frame(self, method, *args):
        return self.ovirt_driver.execute_in_frame(
            self.DASHBOARD_IFRAME_SELECTOR, method, *args
        )

    def _is_displayed(self):
        return self.ovirt_driver.driver.find_element(
            By.XPATH, '//div[@id="global-dashboard"]'
        ).is_displayed()

    def _get_aggregate_count(self, label):
        return int(
            self.ovirt_driver.driver.find_element(
                By.XPATH,
                '//a[span/text() = "'
                + label
                + '"]/span[@class="aggregate-status-count"]',
            ).text
        )
