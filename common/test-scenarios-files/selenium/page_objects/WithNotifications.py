from .WithOvirtDriver import WithOvirtDriver

class WithNotifications(WithOvirtDriver):

    def is_error_notification_visible(self):
        xpath = '//div[contains(@class, "alert-danger")]'
        return self.ovirt_driver.retry_if_stale(self.ovirt_driver.is_xpath_present, xpath) and self.ovirt_driver.retry_if_stale(self.ovirt_driver.is_xpath_displayed, xpath)

    def _is_notification_displayed(self):
        xpath = '//a[@class="notif_dismissButton"]'
        result = self.ovirt_driver.is_xpath_present(xpath) and self.ovirt_driver.is_xpath_displayed(xpath)
        return result

    def close_notification_safely(self):
        xpath = '//a[@class="notif_dismissButton"]'
        if self._is_notification_displayed():
            print('Notification is present')
            self.ovirt_driver.xpath_click(xpath)
            self.ovirt_driver.wait_while(self.ovirt_driver.is_xpath_displayed, xpath)
            print('Notification was closed')

    def wait_and_close_success_notification_safely(self):
        isError = False

        print('Wait for notification')
        xpath = '//a[@class="notif_dismissButton"]'
        self.ovirt_driver.wait_long_until('Notification is not displayed', self.ovirt_driver.is_xpath_displayed, xpath)
        self.ovirt_driver.wait_long_until('Notification is not enabled', self.ovirt_driver.is_xpath_enabled, xpath)

        isError = self.is_error_notification_visible()
        if isError:
            raise Exception("Unexpected error notification present")
        else:
            self.ovirt_driver.xpath_click(xpath)
            print('Notification closed')

