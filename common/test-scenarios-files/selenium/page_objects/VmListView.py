from .constants import *
from .Displayable import Displayable
from .WithBreadcrumbs import WithBreadcrumbs
from .VmDetailView import VmDetailView

class VmListView(Displayable,WithBreadcrumbs):

    def __init__(self, ovirt_driver):
        super(VmListView, self).__init__(ovirt_driver)

    def is_displayed(self):
        breadcrumbs = self.get_breadcrumbs()
        return len(breadcrumbs) == 2 and breadcrumbs[0] == BREADCRUMB_VM_COMPUTE and breadcrumbs[1] == BREADCRUMB_VM_LIST

    def open_detail_view(self, vm_name):
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_vm_names_to_ids)

        if vm_name in names_to_ids:
            self.ovirt_driver.id_click(names_to_ids[vm_name])

            vm_detail_view = VmDetailView(self.ovirt_driver, vm_name)
            vm_detail_view.wait_for_displayed()
            return vm_detail_view
        else:
            raise Exception("No virtual machine with the name " + vm_name + " found")

    def get_vms(self):
        names_to_ids = self.ovirt_driver.retry_if_stale(self._get_vm_names_to_ids)
        vms = []
        for name in names_to_ids:
            vms.append(name)
        return vms

    def _get_vm_names_to_ids(self):
        elements = self.ovirt_driver.driver.find_elements_by_css_selector('a[id^="MainVirtualMachineView_table_content_col2_row"')
        names_to_ids = {}
        for element in elements:
            names_to_ids[element.text] = element.get_attribute('id')

        return names_to_ids
