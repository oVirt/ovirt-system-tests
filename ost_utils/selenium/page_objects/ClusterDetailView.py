#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .EntityDetailView import EntityDetailView


class ClusterDetailView(EntityDetailView):
    def __init__(self, ovirt_driver, breadcrumbs, cluster_name):
        super(ClusterDetailView, self).__init__(ovirt_driver, breadcrumbs, cluster_name)

    def get_displayable_name(self):
        return 'Cluster detail view'

    def get_name(self):
        return self.ovirt_driver.find_element(By.ID, 'SubTabClusterGeneralView_form_col0_row0_value').text

    def get_description(self):
        return self.ovirt_driver.find_element(By.ID, 'SubTabClusterGeneralView_form_col0_row1_value').text
