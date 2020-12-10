from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs
from .WithNotifications import WithNotifications

class EntityListView(Displayable,WithBreadcrumbs,WithNotifications):

    def __init__(self, ovirt_driver, entity_type, breadcrumbs, entity_name_table_cell_id_selector):
        super(EntityListView, self).__init__(ovirt_driver)
        self.entity_type = entity_type
        self.breadcrumbs = breadcrumbs
        self.entity_name_table_cell_id_selector = entity_name_table_cell_id_selector

    def is_displayed(self):
        current_breadcrumbs = self.get_breadcrumbs()
        breadcrumbs_present = len(current_breadcrumbs) == 2 and current_breadcrumbs[0] == self.breadcrumbs[0] and current_breadcrumbs[1] == self.breadcrumbs[1]
        entity_present = self.ovirt_driver.is_xpath_present('//a[contains(@id, "' + self.entity_name_table_cell_id_selector + '")]')
        no_entity_present = self.ovirt_driver.is_xpath_present('//*[text() = "No items to display"]')
        return breadcrumbs_present and (entity_present or no_entity_present)

    def get_displayable_name(self):
        return self.entity_type.capitalize() + ' list view'

    def open_detail_view(self, entity_name):
        print('Open detail of ' + self.entity_type + ' ' + entity_name)
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_entity_names_to_ids)

        if entity_name in names_to_ids:
            self.ovirt_driver.id_click(names_to_ids[entity_name])
        else:
            raise Exception('No ' + self.entity_type + ' with the name ' + entity_name + ' found')

    def select_entity(self, entity_name):
        print('Select ' + self.entity_type + ' ' + entity_name)
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_entity_names_to_ids)

        if entity_name in names_to_ids:
            self.ovirt_driver.xpath_click('//*[@id="' + names_to_ids[entity_name]  + '"]/..')
        else:
            raise Exception('No ' + self.entity_type + ' with the name ' + entity_name + ' found')

    def get_entities(self):
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_entity_names_to_ids)
        entities = []
        for name in names_to_ids:
            entities.append(name)
        return entities

    def _get_entity_names_to_ids(self):
        elements = self.ovirt_driver.driver.find_elements_by_xpath('//a[contains(@id, "' + self.entity_name_table_cell_id_selector + '")]')
        names_to_ids = {}
        for element in elements:
            names_to_ids[element.text] = element.get_attribute('id')

        return names_to_ids

