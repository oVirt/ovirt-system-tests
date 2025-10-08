#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from .EntityListView import EntityListView
from .HostDetailView import HostDetailView
from .HostDialog import HostDialog


class HostListView(EntityListView):
    def __init__(self, ovirt_driver):
        super(HostListView, self).__init__(
            ovirt_driver,
            'host',
            ['Compute', 'Hosts'],
            'MainHostView_table_content_col2_row',
        )

    def open_detail_view(self, entity_name):
        super().open_detail_view(entity_name)

        detail_view = HostDetailView(self.ovirt_driver, self.breadcrumbs, entity_name)
        detail_view.wait_for_displayed()
        return detail_view

    def edit(self, entity_name):
        super().edit(entity_name)

        dialog = HostDialog(self.ovirt_driver, 'Edit')
        dialog.wait_for_displayed()
        return dialog

    def is_new_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Edit')

    def is_remove_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Remove')

    def is_management_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Management')

    def is_install_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Installation')

    def is_host_console_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Host Console')
