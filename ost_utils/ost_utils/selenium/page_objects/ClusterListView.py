from .EntityListView import EntityListView


class ClusterListView(EntityListView):
    def __init__(self, ovirt_driver):
        super(ClusterListView, self).__init__(
            ovirt_driver,
            'cluster',
            ['Compute', 'Clusters'],
            'MainClusterView_table_content_col1_row',
        )

    def is_new_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Edit')

    def is_upgrade_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Upgrade')
