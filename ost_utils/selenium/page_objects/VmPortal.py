#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from .Displayable import Displayable


class VmPortal(Displayable):
    def __init__(self, ovirt_driver):
        super(VmPortal, self).__init__(ovirt_driver)

    def is_displayed(self):
        return self.ovirt_driver.is_id_present(
            'page-router-render-component'
        ) and not self.ovirt_driver.is_class_name_present('spinner')

    def get_displayable_name(self):
        return 'VM Portal'

    def get_vm_status(self, vm_name):
        return self.ovirt_driver.driver.find_element(By.ID, 'vm-' + vm_name + '-status').text.strip()

    def get_vm_count(self):
        return int(
            self.ovirt_driver.driver.find_element(By.XPATH, "//div[@class='col-sm-12']/h5").text.strip().split(' ')[0]
        )

    def logout(self):
        self.ovirt_driver.xpath_wait_and_click('User dropdown menu', '//*[@id="usermenu-user"]')
        self.ovirt_driver.wait_until('Logout menu is present', self.ovirt_driver.is_id_present, 'usermenu-logout')

        logout_menu = self.ovirt_driver.driver.find_element(By.XPATH, '//*[@id="usermenu-logout"]')
        ActionChains(self.ovirt_driver.driver).move_to_element(logout_menu).click(logout_menu).perform()

        self.ovirt_driver.wait_while('Vm portal still displayed', self.is_displayed)
