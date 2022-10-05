#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By

from .Displayable import Displayable
from .EntityDetailView import EntityDetailView

LOGGER = logging.getLogger(__name__)


class VmDetailView(EntityDetailView):
    def __init__(self, ovirt_driver, breadcrumbs, vm_name):
        super(VmDetailView, self).__init__(ovirt_driver, breadcrumbs, vm_name)

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

    def get_description(self):
        return self.ovirt_driver.find_element(By.ID, 'SubTabVirtualMachineGeneralView_form_col0_row1_value').text

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
        dialog = self.ovirt_driver.find_dialog_root('vm-manage-gpu-modal', True)
        modal_text = dialog.find_element(By.ID, 'vm-manage-gpu-modal').text
        return 'Select vGPU type' in modal_text

    def get_displayable_name(self):
        return 'Manage vGPU dialog'

    def get_title(self):
        dialog = self.ovirt_driver.find_dialog_root('vm-manage-gpu-modal')
        return dialog.find_element(
            By.CSS_SELECTOR,
            'h4.modal-title,h1.pf-c-title,h1.pf-c-modal-box__title',
        ).text

    def get_row_data(self, row_index):
        """Access and extract td text for a given row in the vGPU table.
        row_index is the 1-based indexed row to return
        """

        dialog = self.ovirt_driver.find_dialog_root('vm-manage-gpu-modal')
        tbodys = dialog.find_elements(By.CSS_SELECTOR, 'table.vgpu-table > tbody')

        # the list is 0-base but the index is 1-based so adjust
        row = tbodys[row_index - 1]
        row_tds = row.find_elements(By.CSS_SELECTOR, 'tr>td')
        return list(map(lambda td: td.text, row_tds))

    def cancel(self):
        LOGGER.debug('Cancel vGPU dialog')
        dialog = self.ovirt_driver.find_dialog_root('vm-manage-gpu-modal')
        cancel_button = next(
            (b for b in dialog.find_elements(By.CSS_SELECTOR, 'footer>button') if "Cancel" in b.text),
            None,
        )
        assert cancel_button is not None
        cancel_button.click()

        self.wait_for_not_displayed()
