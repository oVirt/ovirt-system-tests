from .constants import *
from .VmListView import VmListView

class WebAdminLeftMenu:

    def __init__(self, ovirt_driver):
        self.ovirt_driver = ovirt_driver

    def open_vm_list_view(self):
        print('Open VM list view')
        self.ovirt_driver.hover_to_id(SEL_ID_COMPUTE_MENU)
        self.ovirt_driver.id_click(SEL_ID_VMS_MENU)

        vm_list_view = VmListView(self.ovirt_driver)
        vm_list_view.wait_for_displayed()
        return vm_list_view

