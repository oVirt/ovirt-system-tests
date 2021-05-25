import logging

from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class WelcomeScreen(Displayable):

    def __init__(self, ovirt_driver):
        super(WelcomeScreen, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.driver.find_element_by_class_name('welcome-section').is_displayed()

    def get_displayable_name(self):
        return 'Welcome screen'

    def open_administration_portal(self):
        LOGGER.debug('Open Administration portal')
        self.ovirt_driver.driver.find_element_by_id('WelcomePage_webadmin').click()

    def open_user_portal(self):
        LOGGER.debug('Open User portal')
        self.ovirt_driver.driver.find_element_by_id('WelcomePage_userportal_webui').click()

    def open_monitoring_portal(self):
        LOGGER.debug('Open Monitoring portal')
        self.ovirt_driver.driver.find_element_by_id('WelcomePage_monitoring_grafana').click()

    def logout(self):
        self.ovirt_driver.xpath_wait_and_click('User dropdown menu','//*[@id="sso-dropdown-toggle"]')
        self.ovirt_driver.xpath_wait_and_click('Logout menu',"//li[1]/a[@class='pf-c-dropdown__menu-item']")

    def is_user_logged_in(self, username):
        return self.ovirt_driver.driver.find_element_by_xpath(
            '//*[@id="sso-dropdown-toggle"]').text.strip().split('@')[0] == username

    def is_user_logged_out(self):
        return self.ovirt_driver.driver.find_element_by_xpath('//button[@id="sso-dropdown-toggle"]/span').text.strip() == 'Not logged in'

    def is_error_message_displayed(self):
        return self.ovirt_driver.driver.find_element_by_class_name('session-error').is_displayed()

    def get_error_message(self):
        return self.ovirt_driver.driver.find_element_by_class_name('pf-c-alert__title').text.strip()
