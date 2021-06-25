import logging
import time
from selenium.webdriver.common.action_chains import ActionChains
from .Displayable import Displayable
from .VmListView import VmListView
from .TemplateListView import TemplateListView
from .PoolListView import PoolListView
from .HostListView import HostListView
from .ClusterListView import ClusterListView
from .StorageDomainListView import StorageDomainListView
from .DisksListView import DisksListView
from .DashboardView import DashboardView

LOGGER = logging.getLogger(__name__)


class WebAdminLeftMenu(Displayable):

    def __init__(self, ovirt_driver):
        super(WebAdminLeftMenu, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.is_class_name_present('nav-pf-vertical-collapsible-menus')

    def get_displayable_name(self):
        return 'WebAdmin left menu'

    def open_dashboard_view(self):
        LOGGER.debug('Open dashboard view')
        self._open_dashboard_menu()

        dashboard = DashboardView(self.ovirt_driver)
        dashboard.wait_for_displayed()
        return dashboard

    def open_vm_list_view(self):
        LOGGER.debug('Open VM list view')
        self._open_compute_menu('VMx', 'MenuView_vmsAnchor')

        vm_list_view = VmListView(self.ovirt_driver)
        vm_list_view.wait_for_displayed()
        return vm_list_view

    def open_template_list_view(self):
        LOGGER.debug('Open VM template list view')
        self._open_compute_menu('Templatex', 'MenuView_templatesAnchor')

        template_list_view = TemplateListView(self.ovirt_driver)
        template_list_view.wait_for_displayed()
        return template_list_view

    def open_pool_list_view(self):
        LOGGER.debug('Open VM pool list view')
        self._open_compute_menu('Pools', 'MenuView_poolsAnchor')

        pool_list_view = PoolListView(self.ovirt_driver)
        pool_list_view.wait_for_displayed()
        return pool_list_view

    def open_host_list_view(self):
        LOGGER.debug('Open host list view')
        self._open_compute_menu('Hosts', 'MenuView_hostsAnchor')

        host_list_view = HostListView(self.ovirt_driver)
        host_list_view.wait_for_displayed()
        return host_list_view

    def open_cluster_list_view(self):
        LOGGER.debug('Open cluster list view')
        self._open_compute_menu('Clusters', 'MenuView_clustersAnchor')

        cluster_list_view = ClusterListView(self.ovirt_driver)
        cluster_list_view.wait_for_displayed()
        return cluster_list_view

    def open_storage_domain_list_view(self):
        LOGGER.debug('Open storage domain list view')
        self._open_storage_menu('Storage Domains', 'MenuView_domainsAnchor')

        storage_domain_list_view = StorageDomainListView(self.ovirt_driver)
        storage_domain_list_view.wait_for_displayed()
        return storage_domain_list_view

    def open_disks_list_view(self):
        LOGGER.debug('Open disks list view')
        self._open_storage_menu('Storage Domains', 'MenuView_disksAnchor')

        disks_list_view = DisksListView(self.ovirt_driver)
        disks_list_view.wait_for_displayed()
        return disks_list_view

    def _open_dashboard_menu(self):
        self.ovirt_driver.xpath_wait_and_click('Dashboard menu', '//a[@href="#dashboard-main"]')

    def _open_compute_menu(self, menu_name, menu_id):
        self._open_menu('compute', menu_name, menu_id)

    def _open_storage_menu(self, menu_name, menu_id):
        self._open_menu('MenuView_storageTab', menu_name, menu_id)

    def _open_menu(self, menu_group, menu_name, menu_id):
        menu_element = self.ovirt_driver.driver.find_element_by_id(menu_group)
        submenu_element = self.ovirt_driver.driver.find_element_by_id(menu_id)
        self.ovirt_driver.wait_until(f'sub menu "{menu_name}" is visible  in the left menu',
                self._submenu_is_displayed,
                menu_element,
                submenu_element)
        submenu_element.click()

    def _submenu_is_displayed(self, menu_element, submenu_element):
        ActionChains(self.ovirt_driver.driver).move_to_element(menu_element).perform()
        return submenu_element.is_displayed()
