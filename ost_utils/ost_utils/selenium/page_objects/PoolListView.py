from .EntityListView import EntityListView


class PoolListView(EntityListView):
    def __init__(self, ovirt_driver):
        super(PoolListView, self).__init__(
            ovirt_driver,
            'pool',
            ['Compute', 'Pools'],
            'MainPoolView_table_content_col1_row',
        )

    def is_new_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Edit')

    def is_remove_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Remove')
