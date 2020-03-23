from .constants import *
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs
from .VmDetailView import VmDetailView
from selenium.common.exceptions import NoSuchElementException

class VmListView(Displayable,WithBreadcrumbs):

    def __init__(self, ovirt_driver):
        super(VmListView, self).__init__(ovirt_driver)

    def is_displayed(self):
        breadcrumbs = self.get_breadcrumbs()
        return len(breadcrumbs) == 2 and breadcrumbs[0] == BREADCRUMB_VM_COMPUTE and breadcrumbs[1] == BREADCRUMB_VM_LIST

    def get_displayable_name(self):
        return 'VM list view'

    def open_detail_view(self, vm_name):
        print('Open detail of vm ' + vm_name)
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_vm_names_to_ids)

        if vm_name in names_to_ids:
            self.ovirt_driver.id_click(names_to_ids[vm_name])

            vm_detail_view = VmDetailView(self.ovirt_driver, vm_name)
            vm_detail_view.wait_for_displayed()
            return vm_detail_view
        else:
            raise Exception("No virtual machine with the name " + vm_name + " found")

    def select_vm(self, vm_name):
        print('Select vm ' + vm_name)
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_vm_names_to_ids)

        if vm_name in names_to_ids:
            self.ovirt_driver.retry_if_stale(self._xpath_click, '//*[@id="' + names_to_ids[vm_name]  + '"]/..')
        else:
            raise Exception("No virtual machine with the name " + vm_name + " found")

    def get_vms(self):
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_vm_names_to_ids)
        vms = []
        for name in names_to_ids:
            vms.append(name)
        return vms

    def is_new_button_enabled(self):
        return self.ovirt_driver.retry_if_stale(self._is_button_enabled, 'New')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.retry_if_stale(self._is_button_enabled, 'Edit')

    def is_shutdown_button_enabled(self):
        return self.ovirt_driver.retry_if_stale(self._is_button_enabled, 'Shutdown')

    def is_export_button_enabled(self):
        return self.ovirt_driver.retry_if_stale(self._is_button_enabled, 'Export')

    def is_migrate_button_enabled(self):
        return self.ovirt_driver.retry_if_stale(self._is_button_enabled, 'Migrate')

    def poweroff(self):
        print('Power off selected vm')
        self.close_notification_safely()
        self.ovirt_driver.retry_if_stale(self._xpath_click, '//div[@id="ActionPanelView_Shutdown"]/button[@data-toggle="dropdown"]')
        self.ovirt_driver.retry_if_stale(self._xpath_click, '//div[@id="ActionPanelView_Shutdown"]//a[text()="Power Off"]')

        self._button_wait_and_click('OK')
        self.wait_and_close_success_notification_safely()
        self.ovirt_driver.wait_while('Shutdown button is still enabled', self.is_shutdown_button_enabled)

    def run_once(self):
        print('Run once selected vm')
        self.close_notification_safely()
        self.ovirt_driver.retry_if_stale(self._xpath_click, '//div[@id="ActionPanelView_Run"]/button[@data-toggle="dropdown"]')
        self.ovirt_driver.retry_if_stale(self._xpath_click, '//div[@id="ActionPanelView_Run"]//a[text()="Run Once"]')

        self._xpath_wait_and_click('Button Run', '//div[@id="VmRunOncePopupView_OnRunOnce"]/button[text()="OK"]')
        # To shorten the test execution time we are not waiting for the success notification to appear. The tests have to
        # implement their own wait logic (e.g wait only for Powering Up state)
        self.ovirt_driver.wait_while('Run button is still enabled', self._is_button_enabled, "Run")

    def is_error_notification_visible(self):
        xpath = '//div[contains(@class, "alert-danger")]'
        return self.ovirt_driver.retry_if_stale(self._is_xpath_present, xpath) and self.ovirt_driver.retry_if_stale(self._is_xpath_displayed, xpath)

    def _is_notification_displayed(self):
        xpath = '//a[@class="notif_dismissButton"]'
        result = self._is_xpath_present(xpath) and self._is_xpath_displayed(xpath)
        return result

    def close_notification_safely(self):
        xpath = '//a[@class="notif_dismissButton"]'
        if self._is_notification_displayed():
            print('Notification is present')
            self.ovirt_driver.retry_if_stale(self._xpath_click, xpath)
            self.ovirt_driver.wait_while(self._is_xpath_displayed, xpath)
            print('Notification was closed')

    def wait_and_close_success_notification_safely(self):
        isError = False

        print('Wait for notification')
        xpath = '//a[@class="notif_dismissButton"]'
        self.ovirt_driver.wait_long_until('Notification is not displayed', self._is_xpath_displayed, xpath)
        self.ovirt_driver.wait_long_until('Notification is not enabled', self._is_xpath_enabled, xpath)

        isError = self.is_error_notification_visible()
        if isError:
            raise Exception("Unexpected error notification present")
        else:
            self.ovirt_driver.retry_if_stale(self._xpath_click, xpath)
            print('Notification closed')

    def _get_vm_names_to_ids(self):
        elements = self.ovirt_driver.driver.find_elements_by_css_selector('a[id^="MainVirtualMachineView_table_content_col2_row"]')
        names_to_ids = {}
        for element in elements:
            names_to_ids[element.text] = element.get_attribute('id')

        return names_to_ids

    def _button_wait_and_click(self, text):
        return self._xpath_wait_and_click('Button ' + text, '//button[text()="' + text + '"]')

    def _xpath_wait_and_click(self, message, xpath, wait_long=False):
        wait_until = self.ovirt_driver.wait_until
        if wait_long:
            wait_until = self.ovirt_driver.wait_long_until

        wait_until(message + ' is not displayed', self._is_xpath_displayed, xpath)
        wait_until(message + ' is not enabled', self._is_xpath_enabled, xpath)
        self.ovirt_driver.retry_if_stale(self._xpath_click, xpath)

    def _is_xpath_present(self, xpath):
        try:
            self.ovirt_driver.driver.find_element_by_xpath(xpath)
            return True
        except NoSuchElementException:
            return False

    def _is_button_displayed(self, text):
        return self._is_xpath_displayed('//button[text()="' + text + '"]')

    def _is_xpath_displayed(self, xpath):
        return self.ovirt_driver.driver.find_element_by_xpath(xpath).is_displayed()

    def _is_button_enabled(self, text):
        return self._is_xpath_enabled('//button[text()="' + text + '"]')

    def _is_xpath_enabled(self, xpath):
        return self.ovirt_driver.driver.find_element_by_xpath(xpath).is_enabled()

    def _button_click(self, xpath):
        self._xpath_click('//button[text()="' + xpath + '"]')

    def _xpath_click(self, xpath):
        self.ovirt_driver.driver.find_element_by_xpath(xpath).click()
