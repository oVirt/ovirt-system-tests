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

    def is_export_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Export')

    def is_migrate_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Migrate')

    def poweroff(self):
        LOGGER.debug('Power off selected vm')
        self.close_notification_safely()
        self.click_menu_dropdown_button(
            'ActionPanelView_Shutdown', 'Power Off'
        )

        self.ovirt_driver.button_wait_and_click('OK')
        # TODO this was using wait_and_close_success_notification_safely but
        # it didn't work reliably. ust waiting on shutdown button disable is
        # good enough since it means the VM is down
        self.close_notification_safely()
        self.ovirt_driver.wait_while(
            'Shutdown button is still enabled', self.is_shutdown_button_enabled
        )

    def run_once(self):
        LOGGER.debug('Open run once dialog')
        self.close_notification_safely()
        self.click_menu_dropdown_button('ActionPanelView_Run', 'Run Once')

        run_once_dialog = RunOnceDialog(self.ovirt_driver)
        run_once_dialog.wait_for_displayed()
        return run_once_dialog

    def open_console(self):
        LOGGER.debug('Open console')
        self.click_menu_dropdown_top_button(
            'ActionPanelView_ConsoleConnectCommand'
        )

        novnc_console = NoVncConsole(self.ovirt_driver)
        novnc_console.wait_for_displayed()
        return novnc_console


class RunOnceDialog(Displayable):
    def __init__(self, ovirt_driver):
        super(RunOnceDialog, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.is_xpath_displayed(
            '//*[@id="VmRunOncePopupWidget"]'
        )

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


class NoVncConsole(Displayable):
    def __init__(self, ovirt_driver):
        super(NoVncConsole, self).__init__(ovirt_driver)

    def is_displayed(self):
        if len(self.ovirt_driver.driver.window_handles) < 2:
            return False

        if (
            self.ovirt_driver.driver.current_window_handle
            is not self.ovirt_driver.driver.window_handles[1]
        ):
            self.ovirt_driver.driver.switch_to.window(
                self.ovirt_driver.driver.window_handles[1]
            )
        return self.ovirt_driver.is_xpath_displayed('//div[@id="status"]')

    def get_displayable_name(self):
        return 'Run once dialog'

    def wait_for_loaded(self):
        LOGGER.debug('Wait for VNC console to be loaded')
        self.ovirt_driver.wait_long_while(
            'VNC console is still loading',
            self.ovirt_driver.is_xpath_displayed,
            '//div[@id="status" and text() = "Loading"]',
        )

    def wait_for_connected(self):
        LOGGER.debug('Wait for VNC console to be connected')
        self.ovirt_driver.wait_long_while(
            'VNC console is still connecting',
            self.ovirt_driver.is_xpath_displayed,
            '//div[@id="status" and text() = "Connecting"]',
        )

    def is_connected(self):
        return self.ovirt_driver.is_xpath_displayed(
            '//div[@id="status" and contains(text(), "Connected")]'
        )

    def is_vnc_screen_displayed(self):
        return self.ovirt_driver.is_xpath_displayed(
            '//div[@id="screen"]//canvas'
        )

    def close(self):
        self.ovirt_driver.driver.close()
        self.ovirt_driver.driver.switch_to.window(
            self.ovirt_driver.driver.window_handles[0]
        )
