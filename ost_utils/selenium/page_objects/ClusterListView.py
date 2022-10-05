#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from .ClusterDetailView import ClusterDetailView
from .ClusterDialog import ClusterDialog
from .ClusterUpgradeDialog import ClusterUpgradeDialog
from .EntityListView import EntityListView

LOGGER = logging.getLogger(__name__)


class ClusterListView(EntityListView):
    def __init__(self, ovirt_driver):
        super(ClusterListView, self).__init__(
            ovirt_driver,
            'cluster',
            ['Compute', 'Clusters'],
            'MainClusterView_table_content_col1_row',
        )

    def open_detail_view(self, name):
        super().open_detail_view(name)

        detail_view = ClusterDetailView(self.ovirt_driver, self.breadcrumbs, name)
        detail_view.wait_for_displayed()
        return detail_view

    def edit(self, name):
        super().edit(name)

        dialog = ClusterDialog(self.ovirt_driver, 'Edit')
        dialog.wait_for_displayed()
        return dialog

    def is_new_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Edit')

    def is_upgrade_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Upgrade')

    def upgrade(self, cluster_name):
        LOGGER.debug('Upgrade cluster')
        self.ovirt_driver.xpath_click('//button[text()="Upgrade"]')

        upgrade_dialog = ClusterUpgradeDialog(self.ovirt_driver)
        upgrade_dialog.wait_for_displayed()
        return upgrade_dialog
