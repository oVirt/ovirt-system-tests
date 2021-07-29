from .EntityListView import EntityListView


class TemplateListView(EntityListView):
    def __init__(self, ovirt_driver):
        super(TemplateListView, self).__init__(
            ovirt_driver,
            'template',
            ['Compute', 'Templates'],
            'MainTemplateView_table_content_col1_row',
        )

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
