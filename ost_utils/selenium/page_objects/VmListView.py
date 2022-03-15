#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from .Displayable import Displayable
from .EntityListView import EntityListView
from .VmDetailView import VmDetailView

LOGGER = logging.getLogger(__name__)


class VmListView(EntityListView):
    def __init__(self, ovirt_driver):
        super(VmListView, self).__init__(
            ovirt_driver,
            'vm',
            ['Compute', 'Virtual Machines'],
            'MainVirtualMachineView_table_content_col2_row',
        )

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

    def is_migrate_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Migrate')

    def poweroff(self):
        LOGGER.debug('Power off selected vm')
        self.close_notification_safely()
        self.click_menu_dropdown_button('ActionPanelView_Shutdown', 'Power Off')

        self.ovirt_driver.button_wait_and_click('OK')
        # TODO this was using wait_and_close_success_notification_safely but
        # it didn't work reliably. ust waiting on shutdown button disable is
        # good enough since it means the VM is down
        self.close_notification_safely()
        self.ovirt_driver.wait_while('Shutdown button is still enabled', self.is_shutdown_button_enabled)

    def run_once(self):
        LOGGER.debug('Open run once dialog')
        self.close_notification_safely()
        self.click_menu_dropdown_button('ActionPanelView_Run', 'Run Once')

        run_once_dialog = RunOnceDialog(self.ovirt_driver)
        run_once_dialog.wait_for_displayed()
        return run_once_dialog

    def click_console(self):
        LOGGER.debug('Click console')
        self.click_menu_dropdown_top_button('ActionPanelView_ConsoleConnectCommand')

    def download_console_file(self, console_file_full_path):
        LOGGER.debug(f'Download console.vv file as {console_file_full_path}')
        self.click_console()
        self.ovirt_driver.wait_until(
            'The console.vv file has not been downloaded',
            self._console_file_downloaded,
            console_file_full_path,
        )

    def _console_file_downloaded(self, console_file_full_path):
        try:
            with open(console_file_full_path) as console_file:
                return '-----END CERTIFICATE-----' in console_file.read()
        except FileNotFoundError:
            return False


class RunOnceDialog(Displayable):
    def __init__(self, ovirt_driver):
        super(RunOnceDialog, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.is_xpath_displayed('//*[@id="VmRunOncePopupWidget"]')

    def get_displayable_name(self):
        return 'Run once dialog'

    def toggle_console_options(self):
        LOGGER.debug('Toggle console options')
        self.ovirt_driver.xpath_click('//td[text()="Console"]')

    def select_vnc(self):
        LOGGER.debug('Select VNC')
        self.ovirt_driver.xpath_wait_and_click(
            'VNC radiobutton',
            '//*[@id="VmRunOncePopupWidget_displayConsoleVnc"]',
        )

    def run(self):
        LOGGER.debug('Run once selected vm')
        self.ovirt_driver.xpath_wait_and_click(
            'Button Run',
            '//div[@id="VmRunOncePopupView_OnRunOnce"]/button[text()="OK"]',
        )
        # To shorten the test execution time we are not waiting for the
        # success notification to appear. The tests have to
        # implement their own wait logic (e.g wait only for Powering Up state)
        self.ovirt_driver.wait_while(
            'Run button is still enabled',
            self.ovirt_driver.is_button_enabled,
            "Run",
        )
