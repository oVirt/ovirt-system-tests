from .WithOvirtDriver import WithOvirtDriver


class Displayable(WithOvirtDriver):
    def is_displayed(self):
        # Return False by default to force subclasses to override with proper
        # implementation
        return False

    def get_displayable_name(self):
        return 'Displayable'

    def wait_for_displayed(self):
        self.ovirt_driver.wait_until(
            'Wait until '
            + self.get_displayable_name()
            + ' is displayed failed',
            self.is_displayed,
        )

    def wait_for_not_displayed(self):
        self.ovirt_driver.wait_while(
            self.get_displayable_name() + ' is still displayed',
            self.ovirt_driver.retry_if_stale,
            self.is_displayed,
        )
