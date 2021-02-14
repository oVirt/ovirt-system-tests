import logging

from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class LoginScreen(Displayable):

    def __init__(self, ovirt_driver):
        super(LoginScreen, self).__init__(ovirt_driver)

    def is_displayed(self):
        is_user_name_displayed = self.ovirt_driver.driver.find_element_by_xpath('//input[@id="username"]').is_displayed()
        is_user_password_displayed = self.ovirt_driver.driver.find_element_by_xpath('//input[@id="password"]').is_displayed()
        return is_user_name_displayed and is_user_password_displayed

    def get_displayable_name(self):
        return 'Login screen'

    def set_user_name(self, user_name):
        self.ovirt_driver.driver.find_element_by_xpath('//input[@id="username"]').send_keys(user_name)

    def set_user_password(self, user_password):
        self.ovirt_driver.driver.find_element_by_xpath('//input[@id="password"]').send_keys(user_password)

    def login(self):
        LOGGER.debug('Log in')
        self.ovirt_driver.xpath_click('//form[@id="loginForm"]//button')

