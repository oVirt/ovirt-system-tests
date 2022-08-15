#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging
import time

from selenium.webdriver.common.by import By
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs
from .WithNotifications import WithNotifications

LOGGER = logging.getLogger(__name__)


class EntityListView(Displayable, WithBreadcrumbs, WithNotifications):
    def __init__(
        self,
        ovirt_driver,
        entity_type,
        breadcrumbs,
        entity_name_table_cell_id_selector,
    ):
        super(EntityListView, self).__init__(ovirt_driver)
        self.entity_type = entity_type
        self.breadcrumbs = breadcrumbs
        self.entity_name_table_cell_id_selector = entity_name_table_cell_id_selector

    def is_displayed(self):
        current_breadcrumbs = self.get_breadcrumbs()
        breadcrumbs_present = (
            len(current_breadcrumbs) == 2
            and current_breadcrumbs[0] == self.breadcrumbs[0]
            and current_breadcrumbs[1] == self.breadcrumbs[1]
        )
        entity_present = self.ovirt_driver.is_xpath_present(
            '//a[contains(@id, "' + self.entity_name_table_cell_id_selector + '")]',
        )
        no_entity_present = self.ovirt_driver.is_xpath_present('//*[text() = "No items to display"]')
        return breadcrumbs_present and (entity_present or no_entity_present)

    def get_displayable_name(self):
        return self.entity_type.capitalize() + ' list view'

    def click_menu_dropdown_top_button(self, main_button_id):
        self.ovirt_driver.xpath_click(f'//div[@id="{main_button_id}"]')

    def click_menu_dropdown_button(self, main_button_id, dropdown_button_text):
        self.ovirt_driver.xpath_click(f'//div[@id="{main_button_id}"]/button[@data-toggle="dropdown"]')
        self.ovirt_driver.xpath_click(f'//div[@id="{main_button_id}"]' f'//a[text()="{dropdown_button_text}"]')

    def open_detail_view(self, entity_name):
        LOGGER.debug('Open detail of ' + self.entity_type + ' ' + entity_name)
        names_to_ids = self.ovirt_driver.retry_if_known_issue(self._get_entity_names_to_ids)

        if entity_name in names_to_ids:
            self.ovirt_driver.xpath_click(f'//*[@id="{names_to_ids[entity_name]}"]')
        else:
            raise Exception('No ' + self.entity_type + ' with the name ' + entity_name + ' found')

    def select_entity(self, entity_name):
        LOGGER.debug('Select ' + self.entity_type + ' ' + entity_name)
        names_to_ids = self.ovirt_driver.retry_if_known_issue(self._get_entity_names_to_ids)

        if entity_name in names_to_ids:
            # find the parent td and click the td next to it to select the row
            # clicking the name cell directly might cause to navigate to
            # the entity detail
            self.ovirt_driver.xpath_click(
                '//*[@id="' + names_to_ids[entity_name] + '"]/../../following-sibling::td[1]'
            )
        else:
            raise Exception('No ' + self.entity_type + ' with the name ' + entity_name + ' found')
        # TODO we do asserts on other button states right after throughout
        # the code and it's too flaky. this is an ugly workaround
        time.sleep(1)

    def get_entities(self):
        names_to_ids = self.ovirt_driver.retry_if_known_issue(self._get_entity_names_to_ids)
        entities = []
        for name in names_to_ids:
            entities.append(name)
        return entities

    def get_entity_row_id(self, entity_name):
        names_to_ids = self.ovirt_driver.retry_if_known_issue(self._get_entity_names_to_ids)

        if entity_name not in names_to_ids:
            raise Exception(f'No {self.entity_type} with the name {entity_name} found')

        name_id = names_to_ids[entity_name]
        return name_id.replace(self.entity_name_table_cell_id_selector, '')

    def _get_entity_names_to_ids(self):
        elements = self.ovirt_driver.find_elements(
            By.XPATH,
            '//a[contains(@id, "' + self.entity_name_table_cell_id_selector + '")]',
        )
        names_to_ids = {}
        for element in elements:
            names_to_ids[element.text] = element.get_attribute('id')

        return names_to_ids
