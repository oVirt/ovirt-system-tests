#
# Copyright 2018-2020 Red Hat, Inc.
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
import os
import shutil
import subprocess
import sys
import time

from datetime import datetime

import ovirtsdk4.types as types
import pytest
import test_utils

from ost_utils.pytest.fixtures import api_v4
from ost_utils.pytest.fixtures import prefix
from ost_utils.pytest.fixtures.engine import engine_cert
from ost_utils.pytest.fixtures.engine import engine_fqdn
from ost_utils.pytest.fixtures.engine import engine_ip
from ost_utils.pytest.fixtures.engine import engine_username
from ost_utils.pytest.fixtures.engine import engine_password
from ost_utils.pytest.fixtures.engine import engine_webadmin_url
from ost_utils.pytest.fixtures.selenium import hub_url
from ost_utils.selenium import CHROME_VERSION
from ost_utils.selenium import FIREFOX_VERSION
from ost_utils.shell import ShellError
from ost_utils.shell import shell
from ovirtlago import testlib
from test_utils.constants import *
from test_utils.selenium_constants import *
from test_utils.navigation.driver import *
from test_utils.page_objects.WebAdminLeftMenu import WebAdminLeftMenu

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
def screenshots_dir():
    dc_version = os.environ.get('OST_DC_VERSION', '')
    root = os.environ.get('OST_REPO_ROOT')
    path = os.path.join(root, 'exported-artifacts/screenshots%s/' % dc_version)

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


def test_login(ovirt_driver, save_screenshot, engine_username,
               engine_password, engine_cert):
    """
    login to oVirt webadmin
    """
    save_screenshot('login_screen')
    elem = ovirt_driver.wait_for_id(SEL_ID_LOGIN_USERNAME)
    elem.send_keys(engine_username)
    elem = ovirt_driver.wait_for_id(SEL_ID_LOGIN_PASSWORD)
    elem.send_keys(engine_password)
    save_screenshot('login_screen_credentials')
    elem.send_keys(Keys.RETURN)
    save_screenshot('logged_in', 5)


def test_left_nav(ovirt_driver, save_screenshot, save_page_source):
    """
    click around on a few main views
    """

    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        webadmin_menu.wait_for_displayed()
    except:
        save_screenshot('menu-failed')
        save_page_source('menu-failed')
        raise

    ovirt_driver.hover_to_id(SEL_ID_COMPUTE_MENU)
    save_screenshot('left_nav_hover_compute')
    ovirt_driver.id_click(SEL_ID_CLUSTERS_MENU)
    time.sleep(1)
    save_screenshot('left_nav_clicked_clusters')

    ovirt_driver.hover_to_id(SEL_ID_COMPUTE_MENU)
    save_screenshot('left_nav_hover_compute')
    ovirt_driver.id_click(SEL_ID_HOSTS_MENU)
    save_screenshot('left_nav_clicked_hosts')

    ovirt_driver.hover_to_id(SEL_ID_STORAGE_MENU)
    save_screenshot('left_nav_hover_storage')
    ovirt_driver.id_click(SEL_ID_DOMAINS_MENU)
    save_screenshot('left_nav_clicked_domains')

    ovirt_driver.hover_to_id(SEL_ID_COMPUTE_MENU)
    save_screenshot('left_nav_hover_compute')
    ovirt_driver.id_click(SEL_ID_TEMPLATES_MENU)
    save_screenshot('left_nav_clicked_templates')

    ovirt_driver.hover_to_id(SEL_ID_COMPUTE_MENU)
    save_screenshot('left_nav_hover_compute')
    ovirt_driver.id_click(SEL_ID_POOLS_MENU)
    save_screenshot('left_nav_clicked_pools')

    ovirt_driver.hover_to_id(SEL_ID_COMPUTE_MENU)
    save_screenshot('left_nav_hover_compute')
    ovirt_driver.id_click(SEL_ID_VMS_MENU)
    save_screenshot('left_nav_clicked_vms')


@pytest.fixture
def setup_virtual_machines(api_v4):
    vm_service = test_utils.get_vm_service(api_v4.system_service(), 'vm0')
    if vm_service.get().status == types.VmStatus.DOWN:
        vm_service.start()
        testlib.assert_true_within_long(
            lambda: vm_service.get().status == types.VmStatus.POWERING_UP
        )


def test_virtual_machines(ovirt_driver, setup_virtual_machines,
                          save_screenshot, save_page_source):
    try:
        webadmin_menu = WebAdminLeftMenu(ovirt_driver)
        vm_list_view = webadmin_menu.open_vm_list_view()

        vms = vm_list_view.get_vms()
        assert 'vm0' in vms
        assert vm_list_view.is_new_button_enabled() is True
        assert vm_list_view.is_edit_button_enabled() is False
        assert vm_list_view.is_shutdown_button_enabled() is False
        assert vm_list_view.is_export_button_enabled() is False
        assert vm_list_view.is_migrate_button_enabled() is False

        vm_list_view.select_vm('vm0')
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
