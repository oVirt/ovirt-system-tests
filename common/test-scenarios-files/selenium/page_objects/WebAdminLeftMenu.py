from .constants import *
from .Displayable import Displayable
from .VmListView import VmListView

class WebAdminLeftMenu(Displayable):

    def __init__(self, ovirt_driver):
        super(WebAdminLeftMenu, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.is_class_name_present('nav-pf-vertical-collapsible-menus')

    def get_displayable_name(self):
        return 'WebAdmin left menu'

    def open_vm_list_view(self):
        print('Open VM list view')
        self.ovirt_driver.hover_to_id(SEL_ID_COMPUTE_MENU)
        self.ovirt_driver.id_click(SEL_ID_VMS_MENU)

        vm_list_view = VmListView(self.ovirt_driver)
        vm_list_view.wait_for_displayed()
        return vm_list_view

