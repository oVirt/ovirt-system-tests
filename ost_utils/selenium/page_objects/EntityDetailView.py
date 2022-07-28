#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs


class EntityDetailView(Displayable, WithBreadcrumbs):
    def __init__(self, ovirt_driver, breadcrumbs, entity_name):
        super(EntityDetailView, self).__init__(ovirt_driver)
        self.breadcrumbs = breadcrumbs.copy()
        self.breadcrumbs.append(entity_name)

    def is_displayed(self):
        return self.breadcrumbs == self.get_breadcrumbs()
