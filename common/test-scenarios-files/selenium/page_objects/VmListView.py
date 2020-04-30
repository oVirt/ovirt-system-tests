from .constants import *
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs
from .WithNotifications import WithNotifications
from .VmDetailView import VmDetailView
from selenium.common.exceptions import NoSuchElementException

class VmListView(Displayable,WithBreadcrumbs,WithNotifications):

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
            self.ovirt_driver.xpath_click('//*[@id="' + names_to_ids[vm_name]  + '"]/..')
        else:
            raise Exception("No virtual machine with the name " + vm_name + " found")

    def get_vms(self):
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_vm_names_to_ids)
        vms = []
        for name in names_to_ids:
            vms.append(name)
        return vms

    def is_new_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Edit')

    def is_shutdown_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Shutdown')

    def is_export_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Export')

    def is_migrate_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Migrate')

    def poweroff(self):
        print('Power off selected vm')
        self.close_notification_safely()
        self.ovirt_driver.xpath_click('//div[@id="ActionPanelView_Shutdown"]/button[@data-toggle="dropdown"]')
        self.ovirt_driver.xpath_click('//div[@id="ActionPanelView_Shutdown"]//a[text()="Power Off"]')

        self.ovirt_driver.button_wait_and_click('OK')
        self.wait_and_close_success_notification_safely()
        self.ovirt_driver.wait_while('Shutdown button is still enabled', self.is_shutdown_button_enabled)

    def run_once(self):
        print('Run once selected vm')
        self.close_notification_safely()
        self.ovirt_driver.xpath_click('//div[@id="ActionPanelView_Run"]/button[@data-toggle="dropdown"]')
        self.ovirt_driver.xpath_click('//div[@id="ActionPanelView_Run"]//a[text()="Run Once"]')

        self.ovirt_driver.xpath_wait_and_click('Button Run', '//div[@id="VmRunOncePopupView_OnRunOnce"]/button[text()="OK"]')
        # To shorten the test execution time we are not waiting for the success notification to appear. The tests have to
        # implement their own wait logic (e.g wait only for Powering Up state)
        self.ovirt_driver.wait_while('Run button is still enabled', self.ovirt_driver.is_button_enabled, "Run")

    def _get_vm_names_to_ids(self):
        elements = self.ovirt_driver.driver.find_elements_by_css_selector('a[id^="MainVirtualMachineView_table_content_col2_row"]')
        names_to_ids = {}
        for element in elements:
            names_to_ids[element.text] = element.get_attribute('id')

        return names_to_ids

