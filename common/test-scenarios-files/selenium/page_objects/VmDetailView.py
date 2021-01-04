from .constants import *
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs

class VmDetailView(Displayable,WithBreadcrumbs):

    def __init__(self, ovirt_driver, vmName):
        super(VmDetailView, self).__init__(ovirt_driver)
        self.vmName = vmName

    def is_displayed(self):
        breadcrumbs = self.get_breadcrumbs()
        return len(breadcrumbs) == 3 and breadcrumbs[0] == BREADCRUMB_VM_COMPUTE and breadcrumbs[1] == BREADCRUMB_VM_LIST and breadcrumbs[2] == self.vmName

    def get_displayable_name(self):
        return 'VM detail view'

    def open_host_devices_tab(self):
        print('Open host devices tab')
        self.ovirt_driver.driver.find_element_by_link_text('Host Devices').click()

        vm_detail_host_devices_tab = VmDetailHostDevicesTab(self.ovirt_driver)
        vm_detail_host_devices_tab.wait_for_displayed()
        return vm_detail_host_devices_tab 

    def get_name(self):
        return self.ovirt_driver.driver.find_element_by_id('SubTabVirtualMachineGeneralView_form_col0_row0_value').text

    def get_status(self):
        return self.ovirt_driver.driver.find_element_by_id('SubTabVirtualMachineGeneralView_form_col0_row2_value').text

    def wait_for_statuses(self, statuses):
        print('Waiting for one of the specified VM statuses')
        self.ovirt_driver.wait_long_until('Waiting for the specified VM statuses failed', lambda: self.get_status() in statuses)

class VmDetailHostDevicesTab(Displayable):

    def __init__(self, ovirt_driver):
        super(VmDetailHostDevicesTab, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.driver.find_element_by_xpath('//ul/li[@class="active"]/a[@href="#vms-host_devices"]').is_displayed()

    def get_displayable_name(self):
        return 'VM detail view, host devices tab'

    def open_manage_vgpu_dialog(self):
        print('Open vGPU dialog')
        self.ovirt_driver.driver.find_element_by_xpath('//button[text()="Manage vGPU"]').click()
        vm_vgpu_dialog = VmVgpuDialog(self.ovirt_driver)
        vm_vgpu_dialog.wait_for_displayed()
        return vm_vgpu_dialog

class VmVgpuDialog(Displayable):

    def __init__(self, ovirt_driver):
        super(VmVgpuDialog, self).__init__(ovirt_driver)

    def is_displayed(self):
        dialog_displayed = self.ovirt_driver.driver.find_element_by_css_selector('.modal-dialog,.pf-c-modal-box').is_displayed()
        title_displayed = self.ovirt_driver.driver.find_element_by_css_selector('h4.modal-title,h1.pf-c-title,h1.pf-c-modal-box__title').is_displayed()
        return dialog_displayed and title_displayed

    def get_displayable_name(self):
        return 'Manage vGPU dialog'

    def get_title(self):
        return self.ovirt_driver.driver.find_element_by_css_selector('h4.modal-title,h1.pf-c-title,h1.pf-c-modal-box__title').text

    def cancel(self):
        print('Cancel vGPU dialog')
        self.ovirt_driver.driver.find_element_by_xpath('//div[@class="modal-footer"]//button[. = "Cancel"]|//div[@class="pf-c-modal-box__footer"]//button[contains(@class,"pf-m-link")]|//footer[@class="pf-c-modal-box__footer"]//button[contains(@class,"pf-m-link")]').click()
        self.wait_for_not_displayed()

