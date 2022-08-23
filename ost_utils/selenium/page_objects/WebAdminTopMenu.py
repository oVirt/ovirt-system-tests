#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class WebAdminTopMenu(Displayable):
    def __init__(self, ovirt_driver):
        super(WebAdminTopMenu, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.is_css_selector_displayed('nav')

    def get_displayable_name(self):
        return 'WebAdmin top menu'

    def logout(self):
        LOGGER.debug('Log out')
        # overriding the window.onbeforeunload to prevent an intermittend
        # alert saying
        # Leave site? Changes you made may not be saved.
        self.ovirt_driver.execute_script(
            'window.onbeforeunload = function() ' '{console.log("overriden window.onbeforeunload called")};'
        )
        self.ovirt_driver.xpath_wait_and_click('User dropdown menu', '//*[@id="HeaderView_userName"]')
        self.ovirt_driver.xpath_wait_and_click('Logout menu', '//*[@id="HeaderView_logoutLink"]')
