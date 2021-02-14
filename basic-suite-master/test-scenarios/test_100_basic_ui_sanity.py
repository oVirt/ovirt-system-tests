#
# Copyright 2018-2021 Red Hat, Inc.
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
from __future__ import absolute_import
from __future__ import print_function

import functools
import logging
import os
import shutil
import subprocess
import sys
import time
import requests

from datetime import datetime

import ovirtsdk4.types as types
import pytest
import test_utils

from ost_utils import assertions
from ost_utils.pytest.fixtures.ansible import ansible_host0_facts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.grafana import *
from ost_utils.pytest.fixtures.selenium import hub_url
from ost_utils.pytest.fixtures.virt import cirros_image_glance_template_name
from ost_utils.selenium.constants import *
from ost_utils.selenium.navigation.driver import *
from ost_utils.selenium.page_objects.WelcomeScreen import WelcomeScreen
from ost_utils.selenium.page_objects.LoginScreen import LoginScreen
from ost_utils.selenium.page_objects.WebAdminLeftMenu import WebAdminLeftMenu
from ost_utils.selenium.page_objects.WebAdminTopMenu import WebAdminTopMenu
from ost_utils.selenium.page_objects.VmPortal import VmPortal
from ost_utils.selenium.page_objects.GrafanaLoginScreen import GrafanaLoginScreen
from ost_utils.selenium.page_objects.Grafana import Grafana
from ost_utils.selenium.grid import CHROME_VERSION
from ost_utils.selenium.grid import FIREFOX_VERSION
from ost_utils.shell import ShellError
from ost_utils.shell import shell
from test_utils.constants import *

from selenium import webdriver
from selenium.common.exceptions import (ElementNotVisibleException,
                                        NoSuchElementException,
                                        WebDriverException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

LOGGER = logging.getLogger(__name__)

BROWSER_PLATFORM = 'LINUX'
IMAGE_UPLOAD_DELAY = 30
WINDOW_WIDTH = 1680
WINDOW_HEIGHT = 1050


def test_secure_connection_should_fail_without_root_ca(engine_fqdn, engine_ip,
                                                       engine_webadmin_url):
    with pytest.raises(ShellError) as e:
        shell([
            "curl", "-sS",
            "--resolve", "{}:443:{}".format(engine_fqdn, engine_ip),
            engine_webadmin_url
        ])

    # message is different in el7 and el8 curl versions
    assert "self signed certificate in certificate chain" in e.value.err or \
        "not trusted by the user" in e.value.err


def test_secure_connection_should_succeed_with_root_ca(engine_fqdn, engine_ip,
                                                       engine_cert,
                                                       engine_webadmin_url):
    shell([
        "curl", "-sS",
        "--resolve", "{}:443:{}".format(engine_fqdn, engine_ip),
        "--cacert", engine_cert,
        engine_webadmin_url
    ])


def test_add_grafana_user(grafana_admin_api, engine_email):
    url = grafana_admin_api + '/admin/users'
    data = '''{{
        "name":"ost",
        "email":"{}",
        "login":"ost",
        "password":"ost12345"
    }}'''.format(engine_email)
    headers = {"Content-Type": 'application/json'}

    response = requests.post(url, data=data,headers=headers)

    LOGGER.debug(response.text)


@test_utils.memoized
def firefox_capabilities():
    capabilities = DesiredCapabilities.FIREFOX.copy()
    capabilities['platform'] = BROWSER_PLATFORM
    capabilities['version'] = FIREFOX_VERSION
    capabilities['browserName'] = 'firefox'
    capabilities['acceptInsecureCerts'] = True
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1538486
    capabilities['moz:useNonSpecCompliantPointerOrigin'] = True
    return capabilities


@test_utils.memoized
def chrome_capabilities():
    capabilities = DesiredCapabilities.CHROME.copy()
    capabilities['platform'] = BROWSER_PLATFORM
    capabilities['version'] = CHROME_VERSION
    capabilities['acceptInsecureCerts'] = True
    return capabilities


@pytest.fixture(
    scope="session",
    params=[
        pytest.param(
            firefox_capabilities(),
            id="firefox"
        ),
        pytest.param(
            chrome_capabilities(),
            id="chrome"
        ),
    ]
)
def capabilities(request):
    return request.param


@pytest.fixture(scope="session")
def browser_name(capabilities):
    return capabilities['browserName']


@pytest.fixture(scope="session")
def ovirt_driver(capabilities, hub_url, engine_webadmin_url):
    driver = webdriver.Remote(
        command_executor=hub_url,
        desired_capabilities=capabilities
    )

    ovirt_driver = Driver(driver)
    driver.set_window_size(WINDOW_WIDTH, WINDOW_HEIGHT)
    driver.get(engine_webadmin_url)

    try:
        yield ovirt_driver
    finally:
        ovirt_driver.shutdown()


@pytest.fixture(scope="session")
def screenshots_dir(artifacts_dir):
    dc_version = os.environ.get('OST_DC_VERSION', '')
    path = os.path.join(artifacts_dir, 'screenshots%s/' % dc_version)

    # make screenshot directory
    if os.path.exists(path):
        # clean up old directory
        shutil.rmtree(path)
    os.makedirs(path)
    return path


@pytest.fixture(scope="session")
def save_screenshot(ovirt_driver, browser_name, screenshots_dir):

    def save(description, delay=1):
        date = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        name = "{}_{}_{}.png".format(date, browser_name, description)
        path = os.path.join(screenshots_dir, name)
        ovirt_driver.save_screenshot(path, delay)

    return save


@pytest.fixture(scope="session")
def save_page_source(ovirt_driver, browser_name, screenshots_dir):

    def save(description, delay=1):
        date = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        name = "{}_{}_{}.html".format(date, browser_name, description)
        path = os.path.join(screenshots_dir, name)
        ovirt_driver.save_page_source(path, delay)

    return save


def test_login(ovirt_driver, save_screenshot, save_page_source, engine_username,
               engine_password, engine_cert):

    try:
        save_screenshot('welcome-screen')

        welcome_screen = WelcomeScreen(ovirt_driver)
        welcome_screen.wait_for_displayed()
        welcome_screen.open_administration_portal()

        login_screen = LoginScreen(ovirt_driver)
        login_screen.wait_for_displayed()
        login_screen.set_user_name(engine_username)
        login_screen.set_user_password(engine_password)
        login_screen.login()

        webadmin_left_menu = WebAdminLeftMenu(ovirt_driver)
        webadmin_left_menu.wait_for_displayed()

        webadmin_top_menu = WebAdminTopMenu(ovirt_driver)
        webadmin_top_menu.wait_for_displayed()

        assert webadmin_left_menu.is_displayed()
        assert webadmin_top_menu.is_displayed()

        save_screenshot('login-success')
    except:
        save_screenshot('login-failed')
        save_page_source('login-failed')
        raise


def test_clusters(ovirt_driver, save_screenshot, save_page_source):
    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        cluster_list_view = webadmin_menu.open_cluster_list_view()

        clusters = cluster_list_view.get_entities()
        assert 'test-cluster' in clusters

        cluster_list_view.select_entity('test-cluster')
        assert cluster_list_view.is_new_button_enabled() is True
        assert cluster_list_view.is_edit_button_enabled() is True
        assert cluster_list_view.is_upgrade_button_enabled() is True

        save_screenshot('clusters-success')
    except:
        save_screenshot('clusters-failed')
        save_page_source('clusters-failed')
        raise


def test_hosts(ovirt_driver, ansible_host0_facts, save_screenshot, save_page_source):
    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        host_list_view = webadmin_menu.open_host_list_view()

        host_name = ansible_host0_facts.get("ansible_hostname")
        hosts = host_list_view.get_entities()
        assert host_name in hosts
        assert host_list_view.is_new_button_enabled() is True
        assert host_list_view.is_edit_button_enabled() is False
        assert host_list_view.is_remove_button_enabled() is False
        assert host_list_view.is_management_button_enabled() is False
        assert host_list_view.is_install_button_enabled() is False
        assert host_list_view.is_host_console_button_enabled() is False

        host_list_view.select_entity(host_name)
        assert host_list_view.is_new_button_enabled() is True
        assert host_list_view.is_edit_button_enabled() is True
        assert host_list_view.is_remove_button_enabled() is False
        assert host_list_view.is_management_button_enabled() is True
        assert host_list_view.is_install_button_enabled() is True
        assert host_list_view.is_host_console_button_enabled() is True

        save_screenshot('hosts-success')
    except:
        save_screenshot('hosts-failed')
        save_page_source('hosts-failed')
        raise


def test_templates(ovirt_driver, cirros_image_glance_template_name, save_screenshot, save_page_source):
    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        template_list_view = webadmin_menu.open_template_list_view()

        templates = template_list_view.get_entities()
        assert 'Blank' in templates
        assert cirros_image_glance_template_name in templates
        assert template_list_view.is_new_vm_button_enabled() is False
        assert template_list_view.is_import_button_enabled() is True
        assert template_list_view.is_edit_button_enabled() is False
        assert template_list_view.is_remove_button_enabled() is False
        assert template_list_view.is_export_button_enabled() is False

        template_list_view.select_entity('Blank')
        assert template_list_view.is_new_vm_button_enabled() is True
        assert template_list_view.is_import_button_enabled() is True
        assert template_list_view.is_edit_button_enabled() is True
        assert template_list_view.is_remove_button_enabled() is False
        assert template_list_view.is_export_button_enabled() is False

        template_list_view.select_entity(cirros_image_glance_template_name)
        assert template_list_view.is_new_vm_button_enabled() is True
        assert template_list_view.is_import_button_enabled() is True
        assert template_list_view.is_edit_button_enabled() is True
        assert template_list_view.is_remove_button_enabled() is True
        assert template_list_view.is_export_button_enabled() is True

        save_screenshot('templates-success')
    except:
        save_screenshot('templates-failed')
        save_page_source('templates-failed')
        raise

def test_pools(ovirt_driver, save_screenshot, save_page_source):
    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        pool_list_view = webadmin_menu.open_pool_list_view()

        pools = pool_list_view.get_entities()
        assert not pools
        assert pool_list_view.is_new_button_enabled() is True
        assert pool_list_view.is_edit_button_enabled() is False
        assert pool_list_view.is_remove_button_enabled() is False

        save_screenshot('pools-success')
    except:
        save_screenshot('pools-failed')
        save_page_source('pools-failed')
        raise

@pytest.fixture
def setup_virtual_machines(engine_api):
    vm_service = test_utils.get_vm_service(engine_api.system_service(), 'vm0')
    if vm_service.get().status == types.VmStatus.DOWN:
        vm_service.start()
        assertions.assert_true_within_long(
            lambda: vm_service.get().status == types.VmStatus.POWERING_UP
        )


@pytest.mark.xfail(reason="unstable")
def test_virtual_machines(ovirt_driver, setup_virtual_machines,
                          save_screenshot, save_page_source):
    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        vm_list_view = webadmin_menu.open_vm_list_view()

        vms = vm_list_view.get_entities()
        assert 'vm0' in vms
        assert vm_list_view.is_new_button_enabled() is True
        assert vm_list_view.is_edit_button_enabled() is False
        assert vm_list_view.is_shutdown_button_enabled() is False
        assert vm_list_view.is_export_button_enabled() is False
        assert vm_list_view.is_migrate_button_enabled() is False

        vm_list_view.select_entity('vm0')
        assert vm_list_view.is_new_button_enabled() is True
        assert vm_list_view.is_edit_button_enabled() is True
        assert vm_list_view.is_shutdown_button_enabled() is True
        assert vm_list_view.is_export_button_enabled() is False
        assert vm_list_view.is_migrate_button_enabled() is True

        vm_list_view.poweroff()
        assert vm_list_view.is_new_button_enabled() is True
        assert vm_list_view.is_edit_button_enabled() is True
        assert vm_list_view.is_shutdown_button_enabled() is False
        assert vm_list_view.is_export_button_enabled() is True
        assert vm_list_view.is_migrate_button_enabled() is False

        save_screenshot('vms-list-success')

        vm_detail_view = vm_list_view.open_detail_view('vm0')
        assert vm_detail_view.get_name() == 'vm0'
        assert vm_detail_view.get_status() == 'Down'

        vm_list_view.run_once()
        # Waiting for Powering Up instead of Up to speed up the test execution
        vm_detail_view.wait_for_statuses(['Powering Up', 'Up'])
        vm_status = vm_detail_view.get_status()
        assert vm_status == 'Powering Up' or vm_status == 'Up'
        save_screenshot('vms-after-run-once')

        vm_detail_host_devices_tab = vm_detail_view.open_host_devices_tab()
        vm_vgpu_dialog = vm_detail_host_devices_tab.open_manage_vgpu_dialog()

        assert vm_vgpu_dialog.get_title() == 'Manage vGPU'
        save_screenshot('vms-vgpu')

        vm_vgpu_dialog.cancel()
        save_screenshot('vms-success')
    except:
        save_screenshot('vms-failed')
        save_page_source('vms-failed')
        raise

def test_storage_domains(ovirt_driver, save_screenshot, save_page_source):
    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        storage_domain_list_view = webadmin_menu.open_storage_domain_list_view()

        domains = storage_domain_list_view.get_entities()
        assert 'nfs' in domains
        assert storage_domain_list_view.is_new_button_enabled() is True
        assert storage_domain_list_view.is_import_button_enabled() is True
        assert storage_domain_list_view.is_manage_button_enabled() is False
        assert storage_domain_list_view.is_remove_button_enabled() is False

        storage_domain_list_view.select_entity('nfs')
        assert storage_domain_list_view.is_new_button_enabled() is True
        assert storage_domain_list_view.is_import_button_enabled() is True
        assert storage_domain_list_view.is_manage_button_enabled() is True
        assert storage_domain_list_view.is_remove_button_enabled() is False

        save_screenshot('storage-domains-success')
    except:
        save_screenshot('storage-domains-failed')
        save_page_source('storage-domains-failed')
        raise


@pytest.fixture(scope="session")
def image_local_path():
    # Here we can actually use any file that will be available
    # in most situations (on the node containers, on an external grid, etc.)
    # and readable by the 'seluser' user. '/etc/hostname' seems like
    # a safe and reasonable choice.
    return "/etc/hostname"


def test_image_upload(ovirt_driver, save_screenshot, browser_name,
                      image_local_path):
    image_name = "{}-{}".format(browser_name, int(time.time()))

    # Navigate and upload an image
    ovirt_driver.hover_to_id(SEL_ID_STORAGE_MENU)
    save_screenshot('left_nav_hover_storage')
    ovirt_driver.id_click(SEL_ID_DISKS_MENU)
    save_screenshot('left_nav_clicked_disks')
    ovirt_driver.id_click('ActionPanelView_Upload')
    save_screenshot('left_nav_clicked_upload')
    ovirt_driver.action_on_element('Start', 'click')
    save_screenshot('left_nav_clicked_start')
    ovirt_driver.action_on_element('UploadImagePopupView_fileUpload', 'send',
                                   image_local_path)
    save_screenshot('left_nav_file_uploaded')
    ovirt_driver.action_on_element('VmDiskPopupWidget_alias', 'send',
                                   image_name)
    save_screenshot('left_nav_add_alias')
    ovirt_driver.wait_for_id('UploadImagePopupView_Ok').click()
    # wait for image upload
    time.sleep(IMAGE_UPLOAD_DELAY)
    save_screenshot('left_nav_ok_clicked')


def test_dashboard(ovirt_driver, save_screenshot, save_page_source):
    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        dashboard = webadmin_menu.open_dashboard_view()

        assert dashboard.data_centers_count() is 1
        assert dashboard.clusters_count() is 1
        assert dashboard.hosts_count() is 2
        assert dashboard.storage_domains_count() is 3
        assert dashboard.vm_count() is 6
        assert dashboard.events_count() > 0

        save_screenshot('dashboard-success')
    except:
        save_screenshot('dashboard-failed')
        save_page_source('dashboard-failed')
        raise


def test_logout(ovirt_driver, save_screenshot, save_page_source, engine_webadmin_url):

    try:
        webadmin_menu = WebAdminTopMenu(ovirt_driver)
        webadmin_menu.wait_for_displayed()
        webadmin_menu.logout()

        # navigate directly to welcome page to prevent problems with redirecting to login page instead of welcome page
        ovirt_driver.driver.get(engine_webadmin_url)

        welcome_screen = WelcomeScreen(ovirt_driver)
        welcome_screen.wait_for_displayed()
        assert welcome_screen.is_user_logged_out()

        save_screenshot('logout-success')
    except:
        save_screenshot('logout-failed')
        save_page_source('logout-failed')
        raise


def test_userportal(ovirt_driver, save_screenshot, save_page_source,
        engine_username, engine_password):

    try:
        welcome_screen = WelcomeScreen(ovirt_driver)
        welcome_screen.wait_for_displayed()
        welcome_screen.open_user_portal()

        login_screen = LoginScreen(ovirt_driver)
        login_screen.wait_for_displayed()
        login_screen.set_user_name(engine_username)
        login_screen.set_user_password(engine_password)
        login_screen.login()

        vm_portal = VmPortal(ovirt_driver)
        vm_portal.wait_for_displayed()

        vm0_status = vm_portal.get_vm_status('vm0')
        assert vm0_status == 'Powering up' or vm0_status == 'Running'
        save_screenshot('vm-portal-success')
    except:
        save_screenshot('vm-portal-failed')
        save_page_source('vm-portal-failed')
        raise


def test_grafana(ovirt_driver, save_screenshot, save_page_source, engine_username,
               engine_password, engine_webadmin_url):
    try:

        ovirt_driver.driver.get(engine_webadmin_url)

        welcome_screen = WelcomeScreen(ovirt_driver)
        welcome_screen.wait_for_displayed()
        welcome_screen.open_monitoring_portal()

        grafana_login = GrafanaLoginScreen(ovirt_driver)
        grafana_login.wait_for_displayed()
        save_screenshot('grafana-login')
        grafana_login.use_ovirt_engine_auth()

        grafana = Grafana(ovirt_driver)
        grafana.wait_for_displayed()
        save_screenshot('grafana')

        grafana.open_dashboard('oVirt Executive Dashboards', 'Data Center Dashboard')
        assert not grafana.is_error_visible()
        save_screenshot('grafana-dashboard-1')

        grafana.open_dashboard('oVirt Trend Dashboards', 'Hosts Resource Usage Dashboard')
        assert not grafana.is_error_visible()

        save_screenshot('grafana-dashboard-2')
    except:
        save_screenshot('grafana-failed')
        save_page_source('grafana-failed')
        raise

