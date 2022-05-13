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
            '//h1[text()="Welcome to Grafana"] | ' '//span[text()="Welcome to Grafana"]',
        ).is_displayed()

    def get_displayable_name(self):
        return 'Grafana'

    def open_dashboard(self, menu, submenu):
        LOGGER.debug('Open dashboard ' + menu + '/' + submenu)
        self.ovirt_driver.xpath_wait_and_click('Grafana logo button', '//*[@class="sidemenu__logo"]')
        self.ovirt_driver.xpath_wait_and_click(
            'Home button',
            '//div[@class="navbar"]//a[normalize-space()="Home"] | ' '//button[normalize-space()="Home"]',
        )
        self.ovirt_driver.xpath_wait_and_click(menu, f'//*[text() = "{menu}"]')
        self.ovirt_driver.xpath_wait_and_click(submenu, f'//*[text() = "{submenu}"]')

        self.ovirt_driver.wait_until('Breadcrumbs visible', self._is_breadcrumbs_visible, menu, submenu)

    def is_error_visible(self):
        if self.ovirt_driver.is_xpath_present('//app-notifications-list'):
            notifications = self.ovirt_driver.driver.find_elements(By.XPATH, '//app-notifications-list/*')
            for notification in notifications:
                if "Error" in notification.text:
                    return True
        else:
            raise Exception(
                """Tag app-notifications-list is not present. This may mean that the Graphana
                   UI has changed and we will no longer be able to detect error notifications"""
            )
        return False

    def _is_breadcrumbs_visible(self, menu, submenu):
        find_element = self.ovirt_driver.driver.find_element
        is_breadcrumb_menu_visible = find_element(
            By.XPATH,
            f'//div[@class="navbar-page-btn"]//a[text() = "{menu}"] | ' f'//button[text() = "{menu}"]',
        )
        is_breadcrumb_submenu_visible = find_element(
            By.XPATH,
            f'//div[@class="navbar-page-btn"]//a[text() = "{submenu}"] | ' f'//button[text() = "{submenu}"]',
        )
        return is_breadcrumb_menu_visible and is_breadcrumb_submenu_visible
