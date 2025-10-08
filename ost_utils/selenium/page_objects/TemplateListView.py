#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .EntityListView import EntityListView
from .TemplateDetailView import TemplateDetailView
from .TemplateDialog import TemplateDialog


class TemplateListView(EntityListView):
    def __init__(self, ovirt_driver):
        super(TemplateListView, self).__init__(
            ovirt_driver,
            'template',
            ['Compute', 'Templates'],
            'MainTemplateView_table_content_col1_row',
        )

    def open_detail_view(self, entity_name):
        super().open_detail_view(entity_name)

        detail_view = TemplateDetailView(self.ovirt_driver, self.breadcrumbs, entity_name)
        detail_view.wait_for_displayed()
        return detail_view

    def edit(self, entity_name):
        super().edit(entity_name)

        dialog = TemplateDialog(self.ovirt_driver, 'Edit')
        dialog.wait_for_displayed()
        return dialog

    def is_new_vm_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New VM')

    def is_import_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Import')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Edit')

    def is_remove_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Remove')

    def is_export_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Export')

    def get_status(self, entity_name):
        status_id = f'MainTemplateView_table_content_col5_row{self.get_entity_row_id(entity_name)}'
        status_text = self.ovirt_driver.retry_if_known_issue(
            lambda: self.ovirt_driver.find_element(By.ID, status_id).text
        )
        return status_text
