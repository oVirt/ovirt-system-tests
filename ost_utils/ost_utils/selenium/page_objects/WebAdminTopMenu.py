import logging
import time
from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class WebAdminTopMenu(Displayable):

    def __init__(self, ovirt_driver):
        super(WebAdminTopMenu, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.driver.find_element_by_tag_name('nav').is_displayed()

    def get_displayable_name(self):
        return 'WebAdmin top menu'

    def logout(self):
        LOGGER.debug('Log out')
        self.ovirt_driver.xpath_wait_and_click('User dropdown menu', '//*[@id="HeaderView_userName"]')
        self.ovirt_driver.xpath_wait_and_click('Logout menu', '//*[@id="HeaderView_logoutLink"]')

