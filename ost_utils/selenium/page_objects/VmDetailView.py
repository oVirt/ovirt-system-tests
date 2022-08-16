#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs

LOGGER = logging.getLogger(__name__)


class VmDetailView(Displayable, WithBreadcrumbs):
    def __init__(self, ovirt_driver, vmName):
        super(VmDetailView, self).__init__(ovirt_driver)
        self.vmName = vmName

    def is_displayed(self):
        breadcrumbs = self.get_breadcrumbs()
        return (
            len(breadcrumbs) == 3
            and breadcrumbs[0] == 'Compute'
            and breadcrumbs[1] == 'Virtual Machines'
            and breadcrumbs[2] == self.vmName
        )

    def get_displayable_name(self):
        return 'VM detail view'

    def open_host_devices_tab(self):
        LOGGER.debug('Open host devices tab')
        self.ovirt_driver.find_element(By.LINK_TEXT, 'Host Devices').click()

        vm_detail_host_devices_tab = VmDetailHostDevicesTab(self.ovirt_driver)
        vm_detail_host_devices_tab.wait_for_displayed()
        return vm_detail_host_devices_tab

    def get_name(self):
        return self.ovirt_driver.find_element(By.ID, 'SubTabVirtualMachineGeneralView_form_col0_row0_value').text

    def get_status(self):
        return self.ovirt_driver.find_element(By.ID, 'SubTabVirtualMachineGeneralView_form_col0_row2_value').text

    def wait_for_statuses(self, statuses):
        LOGGER.debug('Waiting for one of the specified VM statuses')
        self.ovirt_driver.wait_long_until(
            'Waiting for the specified VM statuses failed',
            lambda: self.get_status() in statuses,
        )


class VmDetailHostDevicesTab(Displayable):
    def __init__(self, ovirt_driver):
        super(VmDetailHostDevicesTab, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.find_element(
            By.XPATH, '//ul/li[@class="active"]/a[@href="#vms-host_devices"]'
        ).is_displayed()

    def get_displayable_name(self):
        return 'VM detail view, host devices tab'

    def open_manage_vgpu_dialog(self):
        LOGGER.debug('Open vGPU dialog')
        self.ovirt_driver.find_element(
            By.XPATH,
            '//button[text()="Manage vGPU"]',
        ).click()
        vm_vgpu_dialog = VmVgpuDialog(self.ovirt_driver)
        vm_vgpu_dialog.wait_for_displayed()
        return vm_vgpu_dialog


class VmVgpuDialog(Displayable):
    def __init__(self, ovirt_driver):
        super(VmVgpuDialog, self).__init__(ovirt_driver)

    def is_displayed(self):
        dialog_displayed = self.ovirt_driver.find_element(
            By.CSS_SELECTOR, '.modal-dialog,.pf-c-modal-box'
        ).is_displayed()
        spinner_displayed = self.ovirt_driver.is_css_selector_displayed('#vm-manage-gpu-modal .pf-c-spinner')
        return dialog_displayed and not spinner_displayed

    def get_displayable_name(self):
        return 'Manage vGPU dialog'

    def get_title(self):
        return self.ovirt_driver.find_element(
            By.CSS_SELECTOR,
            'h4.modal-title,h1.pf-c-title,h1.pf-c-modal-box__title',
        ).text

    def get_row_data(self, row_index):
        row_tds = self.ovirt_driver.find_elements(
            By.XPATH,
            '//table[contains(@class, "vgpu-table")]/' f'tbody[{row_index}]/tr/td',
        )
        return list(map(lambda td: td.text, row_tds))

    def cancel(self):
        LOGGER.debug('Cancel vGPU dialog')
        self.ovirt_driver.find_element(
            By.XPATH,
            '//div[@class="modal-footer"]//button[. = "Cancel"]|'
            '//div[@class="pf-c-modal-box__footer"]'
            '//button[contains(@class,"pf-m-link")]|'
            '//footer[@class="pf-c-modal-box__footer"]'
            '//button[contains(@class,"pf-m-link")]',
        ).click()
        self.wait_for_not_displayed()
