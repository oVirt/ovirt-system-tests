#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

from ost_utils import assert_utils
from ost_utils import constants
from ost_utils.constants import *
from ost_utils.pytest.fixtures.selenium import *
from ost_utils.pytest.fixtures.ui import *
from ost_utils.selenium.page_objects.WelcomeScreen import WelcomeScreen
from ost_utils.selenium.page_objects.VmPortal import VmPortal
from ost_utils.selenium.page_objects.GrafanaLoginScreen import (
    GrafanaLoginScreen,
)
from ost_utils.selenium.page_objects.Grafana import Grafana


def test_userportal(
    ovirt_driver,
    nonadmin_username,
    nonadmin_password,
    user_login,
    engine_webadmin_url,
    save_screenshot,
):
    welcome_screen = WelcomeScreen(ovirt_driver)
    welcome_screen.wait_for_displayed()
    welcome_screen.open_user_portal()

    user_login(nonadmin_username, nonadmin_password)

    vm_portal = VmPortal(ovirt_driver)
    vm_portal.wait_for_displayed()

    # using vm0 requires logic from 002 _bootstrap::test_add_vm_permissions_to_user
    assert assert_utils.equals_within_short(vm_portal.get_vm_count, 1)
    vm0_status = vm_portal.get_vm_status('vm0')
    assert vm0_status == 'Powering up' or vm0_status == 'Running'
    save_screenshot('userportal')

    vm_portal.logout()
    save_screenshot('userportal-logout')

    welcome_screen = WelcomeScreen(ovirt_driver)
    welcome_screen.wait_for_displayed()
    assert welcome_screen.is_user_logged_out()


def test_grafana(
    ovirt_driver,
    save_screenshot,
    engine_username,
    engine_password,
    engine_webadmin_url,
    user_login,
    engine_fqdn,
):

    ovirt_driver.get(engine_webadmin_url)

    welcome_screen = WelcomeScreen(ovirt_driver)
    welcome_screen.wait_for_displayed()
    welcome_screen.open_monitoring_portal()

    grafana_login = GrafanaLoginScreen(ovirt_driver)
    grafana_login.wait_for_displayed()
    save_screenshot('grafana-login')
    grafana_login.use_ovirt_engine_auth()
    user_login(engine_username, engine_password)

    grafana = Grafana(ovirt_driver)
    grafana.wait_for_displayed()
    save_screenshot('grafana')

    # navigate directly to Grafana Configuration/Data Sources page
    ovirt_driver.get(f'https://{engine_fqdn}/ovirt-engine-grafana/datasources')
    assert grafana.db_connection()
    save_screenshot('grafana-datasource-connection')

    grafana.open_dashboard('oVirt Executive Dashboards', '02 Data Center Dashboard')
    assert not grafana.is_error_visible()
    save_screenshot('grafana-dashboard-1')

    grafana.open_dashboard('oVirt Inventory Dashboards', '02 Hosts Inventory Dashboard')
    assert not grafana.is_error_visible()
    save_screenshot('grafana-dashboard-2')
