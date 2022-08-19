#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By
from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class LoginScreen(Displayable):
    def __init__(self, ovirt_driver, keycloak_enabled):
        super(LoginScreen, self).__init__(ovirt_driver)
        self._keycloak_enabled = keycloak_enabled

    def is_displayed(self):
        is_user_name_displayed = self.ovirt_driver.is_xpath_displayed('//input[@id="username"]')
        is_user_password_displayed = self.ovirt_driver.is_xpath_displayed('//input[@id="password"]')
        return is_user_name_displayed and is_user_password_displayed

    def get_displayable_name(self):
        return 'Login screen'

    def set_user_name(self, user_name):
        self.ovirt_driver.find_element(
            By.XPATH,
            '//input[@id="username"]',
        ).send_keys(user_name)

    def set_user_password(self, user_password):
        self.ovirt_driver.find_element(
            By.XPATH,
            '//input[@id="password"]',
        ).send_keys(user_password)

    def login(self):
        LOGGER.debug('Log in')
        if self._keycloak_enabled:
            self.ovirt_driver.xpath_click('//input[@id="kc-login"]')
        else:
            self.ovirt_driver.xpath_click('//form[@id="loginForm"]//button')
