#
# Copyright 2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from enum import Enum


class Browser(Enum):
    FIREFOX_58 = 'firefox-58'
    CHROME_64 = 'chrome-64'

    def __str__(self):
        return self.value

DRIVER_MAX_RETRIES = 200
DRIVER_SLEEP_TIME = .12
GC_WAIT_TIME = 5
LEFT_NAV_HOVER_TIME = .8
FIREFOX_BROWSER_PROCESS_NAME = 'firefox'
CHROME_BROWSER_PROCESS_NAME = 'chrome'

# selectors

SEL_ID_LOGIN_USERNAME = 'username'
SEL_ID_LOGIN_PASSWORD = 'password'

SEL_ID_VM_REFRESH = 'MainVirtualMachineView_table_refreshPanel_refreshButton'
SEL_ID_VM_ROW_0 = 'MainVirtualMachineView_table_content_col0_row0'
SEL_ID_VM_ROW_X = 'MainVirtualMachineView_table_content_col0_row'
SEL_ID_VM_NAME_COL = 'MainVirtualMachineView_table_content_col2'
SEL_ID_VM_POPUP_CANCEL = 'VmPopupView_Cancel'
SEL_ID_VM_POPUP_OK = 'VmPopupView_OnSave'

SEL_ID_HOST_REFRESH = 'MainHostView_table_refreshPanel_refreshButton'
SEL_ID_HOST_ROW_0 = 'MainHostView_table_content_col0_row0'
SEL_ID_HOST_ROW_X = 'MainHostView_table_content_col0_row'

SEL_ID_USERS_POPUP_CANCEL = 'PermissionsPopupView_Cancel'

SEL_ID_EDIT = 'ActionPanelView_Edit'
SEL_ID_NEW = 'ActionPanelView_New'
SEL_ID_ADD = 'ActionPanelView_Add'
SEL_ID_NEW__VM = "ActionPanelView_NewVm" # bug

# id-network > MenuView_networksAnchor
SEL_ID_COMPUTE_MENU = 'compute'
SEL_ID_STORAGE_MENU = 'MenuView_storageTab'
SEL_ID_ADMINISTRATION_MENU = 'admin'

SEL_ID_HOSTS_MENU = 'MenuView_hostsAnchor'
SEL_ID_VMS_MENU = 'MenuView_vmsAnchor'
SEL_ID_VOLUMES_MENU = 'MenuView_volumesAnchor'
SEL_ID_TEMPLATES_MENU = 'MenuView_templatesAnchor'
SEL_ID_CLUSTERS_MENU = 'MenuView_clustersAnchor'
SEL_ID_DOMAINS_MENU = 'MenuView_domainsAnchor'
SEL_ID_POOLS_MENU = 'MenuView_poolsAnchor'
SEL_ID_USERS_MENU = 'MenuView_usersAnchor'
