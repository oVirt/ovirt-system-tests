from .WithOvirtDriver import WithOvirtDriver


class WithBreadcrumbs(WithOvirtDriver):
    def get_breadcrumbs(self):
        return self.ovirt_driver.retry_if_stale(self._get_breadcrumbs)

    def _get_breadcrumbs(self):
        breadcrumbs_elements = (
            self.ovirt_driver.driver.find_elements_by_css_selector(
                'ol.breadcrumb > li'
            )
        )

        breadcrumbs = []
        for breadcrumbs_element in breadcrumbs_elements:
            breadcrumbs.append(breadcrumbs_element.text)
        return breadcrumbs
