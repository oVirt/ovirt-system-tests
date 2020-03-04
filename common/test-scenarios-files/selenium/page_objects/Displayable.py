from .WithOvirtDriver import WithOvirtDriver
from selenium.webdriver.support.ui import WebDriverWait

class Displayable(WithOvirtDriver):

    def is_displayed(self):
        # Return False by default to force subclasses to override with proper implementation
        return False

    def wait_for_displayed(self):
        self.ovirt_driver.wait_until(self.is_displayed)

    def wait_for_not_displayed(self):
        self.ovirt_driver.wait_while(self.is_displayed)

