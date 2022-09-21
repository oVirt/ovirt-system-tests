#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
import logging

from selenium.webdriver.common.by import By
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs

LOGGER = logging.getLogger(__name__)


class EventsView(Displayable, WithBreadcrumbs):
    def __init__(self, ovirt_driver):
        super(EventsView, self).__init__(ovirt_driver)

    def is_displayed(self):
        breadcrumbs_present = self.get_breadcrumbs() == ['Events', 'Events']
        entity_present = self.ovirt_driver.is_xpath_present('//tr[@__gwt_row = "0"]')
        no_entity_present = self.ovirt_driver.is_xpath_present('//*[text() = "No items to display"]')
        return breadcrumbs_present and (entity_present or no_entity_present)

    def get_displayable_name(self):
        return 'Events view'

    def get_events(self):
        return self.ovirt_driver.retry_if_known_issue(self._get_events)

    def events_contain(self, event_substring):
        return any(event_substring.lower() in event.lower() for event in self.get_events())

    def _get_events(self):
        events_entities = self.ovirt_driver.find_elements(
            By.XPATH,
            '//div[contains(@id, "col2")]',
        )
        return [events_entity.text for events_entity in events_entities]
