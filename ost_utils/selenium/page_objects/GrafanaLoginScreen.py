#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By
from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class GrafanaLoginScreen(Displayable):

    OAUTH_XPATH = '//*[@href="login/generic_oauth"]'

    def __init__(self, ovirt_driver):
        super(GrafanaLoginScreen, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.find_element(By.XPATH, self.OAUTH_XPATH).is_displayed()

    def get_displayable_name(self):
        return 'Grafana login screen'

    def use_ovirt_engine_auth(self):
        LOGGER.debug('Open oVirt Engine Auth')
        self.ovirt_driver.xpath_click(self.OAUTH_XPATH)
