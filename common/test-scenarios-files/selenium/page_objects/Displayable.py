from .WithOvirtDriver import WithOvirtDriver
from selenium.webdriver.support.ui import WebDriverWait

class Displayable(WithOvirtDriver):

    def is_displayed(self):
        # Return False by default to force subclasses to override with proper implementation
        return False

    def wait_for_displayed(self):
        WebDriverWait(self.ovirt_driver.driver, 10).until(IsDisplayedCondition(self))

    def wait_for_not_displayed(self):
        WebDriverWait(self.ovirt_driver.driver, 10).until(IsNotDisplayedCondition(self))

class IsDisplayedCondition(object):
    # An expectation for checking that view is displayed
    def __init__(self, displayable):
        self.displayable = displayable

    def __call__(self, driver):
        try:
            return self.displayable.is_displayed()
        except:
            return False

class IsNotDisplayedCondition(object):
    # An expectation for checking that view is not displayed
    def __init__(self, displayable):
        self.displayable = displayable

    def __call__(self, driver):
        try:
            return not self.displayable.is_displayed()
        except:
            return True

