import logging

from .Displayable import Displayable

LOGGER = logging.getLogger(__name__)


class GrafanaLoginScreen(Displayable):

    OAUTH_XPATH = '//*[@href="login/generic_oauth"]'

    def __init__(self, ovirt_driver):
        super(GrafanaLoginScreen, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.driver.find_element_by_xpath(self.OAUTH_XPATH).is_displayed()

    def get_displayable_name(self):
        return 'Grafana login screen'

    def use_ovirt_engine_auth(self):
        LOGGER.debug('Open oVirt Engine Auth')
        self.ovirt_driver.xpath_click(self.OAUTH_XPATH)

