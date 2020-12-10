from .EntityListView import *
from .VmDetailView import VmDetailView

class VmListView(EntityListView):

    def __init__(self, ovirt_driver):
        super(VmListView, self).__init__(ovirt_driver, 'vm', ['Compute', 'Virtual Machines'], 'MainVirtualMachineView_table_content_col2_row')

    def open_detail_view(self, vm_name):
        super().open_detail_view(vm_name)

        vm_detail_view = VmDetailView(self.ovirt_driver, vm_name)
        vm_detail_view.wait_for_displayed()
        return vm_detail_view

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

