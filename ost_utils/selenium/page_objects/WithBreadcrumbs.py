#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .WithOvirtDriver import WithOvirtDriver


class WithBreadcrumbs(WithOvirtDriver):
    def get_breadcrumbs(self):
        return self.ovirt_driver.retry_if_known_issue(self._get_breadcrumbs)

    def _get_breadcrumbs(self):
        breadcrumbs_elements = self.ovirt_driver.find_elements(By.CSS_SELECTOR, 'ol.breadcrumb > li')

        breadcrumbs = []
        for breadcrumbs_element in breadcrumbs_elements:
            breadcrumbs.append(breadcrumbs_element.text)
        return breadcrumbs
