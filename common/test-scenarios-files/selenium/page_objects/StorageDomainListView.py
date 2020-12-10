from .EntityListView import EntityListView

class StorageDomainListView(EntityListView):

    def __init__(self, ovirt_driver):
        super(StorageDomainListView, self).__init__(ovirt_driver, 'storage domain', ['Storage', 'Storage Domains'], 'MainStorageView_table_content_col2_row')

    def is_new_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New Domain')

    def is_import_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Import Domain')

    def is_manage_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Manage Domain')

    def is_remove_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Remove')

