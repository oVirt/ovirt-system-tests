from .Displayable import Displayable

class GrafanaLoginScreen(Displayable):

    def __init__(self, ovirt_driver):
        super(GrafanaLoginScreen, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.driver.find_element_by_class_name('login-oauth').is_displayed()

    def get_displayable_name(self):
        return 'Grafana login screen'

    def use_ovirt_engine_auth(self):
        print ('Open oVirt Engine Auth')
        self.ovirt_driver.driver.find_element_by_class_name('login-oauth').click()

