#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By
from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class Grafana(Displayable):
    def __init__(self, ovirt_driver):
        super(Grafana, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.driver.find_element(
            By.XPATH,
            '//h1[text()="Welcome to Grafana"] | '
            '//span[text()="Welcome to Grafana"]',
        ).is_displayed()

    def get_displayable_name(self):
        return 'Grafana'

    def open_dashboard(self, menu, submenu):
        LOGGER.debug('Open dashboard ' + menu + '/' + submenu)
        self.ovirt_driver.xpath_wait_and_click(
            'Grafana logo button', '//*[@class="sidemenu__logo"]'
        )
        self.ovirt_driver.xpath_wait_and_click(
            'Home button',
            '//div[@class="navbar"]//a[normalize-space()="Home"] | '
            '//button[normalize-space()="Home"]',
        )
        self.ovirt_driver.xpath_wait_and_click(menu, f'//*[text() = "{menu}"]')
        self.ovirt_driver.xpath_wait_and_click(
            submenu, f'//*[text() = "{submenu}"]'
        )

        self.ovirt_driver.wait_until(
            'Breadcrumbs visible', self._is_breadcrumbs_visible, menu, submenu
        )

    def is_error_visible(self):
        return (
            self.ovirt_driver.is_class_name_present('alert-error')
            and self.ovirt_driver.driver.find_element(
                By.CLASS_NAME, 'alert-error'
            ).is_displayed()
        )

    def _is_breadcrumbs_visible(self, menu, submenu):
        find_element = self.ovirt_driver.driver.find_element
        is_breadcrumb_menu_visible = find_element(
            By.XPATH,
            f'//div[@class="navbar-page-btn"]//a[text() = "{menu}"] | '
            f'//button[text() = "{menu}"]',
        )
        is_breadcrumb_submenu_visible = find_element(
            By.XPATH,
            f'//div[@class="navbar-page-btn"]//a[text() = "{submenu}"] | '
            f'//button[text() = "{submenu}"]',
        )
        return is_breadcrumb_menu_visible and is_breadcrumb_submenu_visible
