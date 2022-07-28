#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from .EntityDetailView import EntityDetailView


class TemplateDetailView(EntityDetailView):
    def __init__(self, ovirt_driver, breadcrumbs, name):
        super(TemplateDetailView, self).__init__(ovirt_driver, breadcrumbs, name)

    def get_displayable_name(self):
        return 'Template detail view'

    def get_name(self):
        return self.ovirt_driver.find_element(By.ID, 'SubTabTemplateGeneralView_form_col0_row0_value').text

    def get_description(self):
        return self.ovirt_driver.find_element(By.ID, 'SubTabTemplateGeneralView_form_col0_row1_value').text
