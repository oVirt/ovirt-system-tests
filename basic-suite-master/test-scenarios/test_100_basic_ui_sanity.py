#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from __future__ import absolute_import
from __future__ import print_function

from datetime import datetime
from functools import cache
import logging
import os
import shutil
import subprocess
import sys
import time

import ovirtsdk4.types as types
import pytest
import requests

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from ost_utils import assert_utils
from ost_utils import test_utils
from ost_utils.constants import *
from ost_utils.pytest.fixtures.ansible import ansible_host0_facts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.selenium import *
from ost_utils.pytest.fixtures.virt import cirros_image_template_name
from ost_utils.selenium.navigation.driver import Driver
from ost_utils.selenium.page_objects.WelcomeScreen import WelcomeScreen
from ost_utils.selenium.page_objects.LoginScreen import LoginScreen
from ost_utils.selenium.page_objects.WebAdminLeftMenu import WebAdminLeftMenu
from ost_utils.selenium.page_objects.WebAdminTopMenu import WebAdminTopMenu
from ost_utils.selenium.page_objects.VmPortal import VmPortal
from ost_utils.selenium.page_objects.GrafanaLoginScreen import (
    GrafanaLoginScreen,
)
from ost_utils.selenium.page_objects.Grafana import Grafana
from ost_utils.shell import ShellError
from ost_utils.shell import shell

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def disable_noisy_logging():
    selenium_logger = logging.getLogger('selenium')
    selenium_logger_level = selenium_logger.getEffectiveLevel()
    selenium_logger.setLevel(logging.WARNING)

    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger_level = urllib3_logger.getEffectiveLevel()
    urllib3_logger.setLevel(logging.WARNING)

    yield

    selenium_logger.setLevel(selenium_logger_level)
    urllib3_logger.setLevel(urllib3_logger_level)


@pytest.fixture(scope="module", autouse=True)
def disable_notifications_for_admin_user(engine_admin_service):
    targetName = "webAdmin.showNotifications"
    existingProps = [option for option in engine_admin_service.options_service().list() if option.name == targetName]
    if not existingProps:
        option = types.UserOption(name=targetName, content="false", user=engine_admin_service.get())
        assert engine_admin_service.options_service().add(option, wait=True)


def test_secure_connection_should_fail_without_root_ca(engine_fqdn, engine_ip_url, engine_webadmin_url):
    with pytest.raises(ShellError) as e:
        shell(
            [
                "curl",
                "-sS",
                "--resolve",
                "{}:443:{}".format(engine_fqdn, engine_ip_url),
                engine_webadmin_url,
            ]
        )

    # message is different in el8 and el9 curl versions
    assert (
        "self signed certificate in certificate chain" in e.value.err
        or "self-signed certificate in certificate chain" in e.value.err
    )


def test_secure_connection_should_succeed_with_root_ca(engine_fqdn, engine_ip_url, engine_cert, engine_webadmin_url):
    shell(
        [
            "curl",
            "-sS",
            "--resolve",
            "{}:443:{}".format(engine_fqdn, engine_ip_url),
            "--cacert",
            engine_cert,
            engine_webadmin_url,
        ]
    )


def test_add_grafana_user(engine_username, engine_password, engine_ip_url, engine_email):
    url = f"http://{engine_username}:{engine_password}@{engine_ip_url}/ovirt-engine-grafana/api/admin/users"
    data = '''{{
        "name":"ost",
        "email":"{}",
        "login":"ost",
        "password":"ost12345"
    }}'''.format(
        engine_email
    )
    headers = {"Content-Type": 'application/json'}

    response = requests.post(url, data=data, headers=headers)

    LOGGER.debug(response.text)


@pytest.fixture(scope="session")
def ovirt_driver(
    engine_webadmin_url, selenium_browser_options, selenium_grid_url, selenium_screen_width, selenium_screen_height
):
    driver = webdriver.Remote(command_executor=selenium_grid_url, options=selenium_browser_options)

    ovirt_driver = Driver(driver)
    driver.set_window_size(selenium_screen_width, selenium_screen_height)
    driver.get(engine_webadmin_url)

    try:
        yield ovirt_driver
    finally:
        ovirt_driver.driver.quit()


@pytest.fixture(scope="session")
def selenium_artifacts_dir(artifacts_dir):
    dc_version = os.environ.get('OST_DC_VERSION', '')
    path = os.path.join(artifacts_dir, 'ui_tests_artifacts%s/' % dc_version)
    os.umask(0)
    os.makedirs(path, mode=0o777, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def selenium_artifact_filename(selenium_browser_name):
    def _selenium_artifact_filename(description, extension):
        date = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return "{}_{}_{}.{}".format(date, selenium_browser_name, description, extension)

    return _selenium_artifact_filename


@pytest.fixture(scope="session")
def selenium_artifact_full_path(selenium_artifacts_dir, selenium_artifact_filename):
    def _selenium_artifact_full_path(description, extension):
        return os.path.join(
            selenium_artifacts_dir,
            selenium_artifact_filename(description, extension),
        )

    return _selenium_artifact_full_path


@pytest.fixture(scope="session")
def console_file_full_path(selenium_artifacts_dir):
    return os.path.join(selenium_artifacts_dir, 'console.vv')


@pytest.fixture(scope="session")
def save_screenshot(ovirt_driver, selenium_artifact_full_path):
    def save(description):
        ovirt_driver.save_screenshot(selenium_artifact_full_path(description, 'png'))

    return save


@pytest.fixture(scope="session")
def save_page_source(ovirt_driver, selenium_artifact_full_path):
    def save(description):
        ovirt_driver.save_page_source(selenium_artifact_full_path(description, 'html'))

    return save


@pytest.fixture(scope="session")
def save_logs_from_browser(ovirt_driver, selenium_artifact_full_path):
    def save(description):
        if ovirt_driver.driver.capabilities['browserName'] == 'chrome':
            ovirt_driver.save_console_log(selenium_artifact_full_path(description, 'txt'))
            ovirt_driver.save_performance_log(selenium_artifact_full_path(description, 'perf.txt'))

    return save


@pytest.fixture(scope="function", autouse=True)
def after_test(request, save_screenshot, save_page_source, save_logs_from_browser):
    yield
    status = "failed" if request.session.testsfailed else "success"
    file_name = f'{request.node.originalname}_{status}'
    save_screenshot(file_name)
    if request.session.testsfailed:
        save_logs_from_browser(file_name)
        save_page_source(file_name)


@pytest.fixture(scope="session")
def user_login(ovirt_driver, keycloak_enabled):
    def login(username, password):
        login_screen = LoginScreen(ovirt_driver, keycloak_enabled)
        login_screen.wait_for_displayed()
        login_screen.set_user_name(username)
        login_screen.set_user_password(password)
        login_screen.login()

    return login


def test_non_admin_login_to_webadmin(
    ovirt_driver,
    nonadmin_username,
    nonadmin_password,
    engine_webadmin_url,
    user_login,
):
    welcome_screen = WelcomeScreen(ovirt_driver)
    welcome_screen.wait_for_displayed()
    welcome_screen.open_administration_portal()
    user_login(nonadmin_username, nonadmin_password)

    assert welcome_screen.is_error_message_displayed()
    assert 'not authorized' in welcome_screen.get_error_message()
    assert welcome_screen.is_user_logged_in(nonadmin_username)
    welcome_screen.logout()
    assert welcome_screen.is_user_logged_out()


def test_login(
    ovirt_driver,
    save_screenshot,
    engine_username,
    engine_password,
    engine_cert,
    keycloak_enabled,
):

    save_screenshot('welcome-screen')

    welcome_screen = WelcomeScreen(ovirt_driver)
    welcome_screen.wait_for_displayed()
    welcome_screen.open_administration_portal()

    login_screen = LoginScreen(ovirt_driver, keycloak_enabled)
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


def test_clusters(ovirt_driver):
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    cluster_list_view = webadmin_menu.open_cluster_list_view()

    clusters = cluster_list_view.get_entities()
    assert 'test-cluster' in clusters

    cluster_list_view.select_entity('test-cluster')
    assert cluster_list_view.is_new_button_enabled() is True
    assert cluster_list_view.is_edit_button_enabled() is True
    assert cluster_list_view.is_upgrade_button_enabled() is True


def test_hosts(ovirt_driver, ansible_host0_facts):
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


def test_templates(ovirt_driver, cirros_image_template_name):
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    template_list_view = webadmin_menu.open_template_list_view()

    templates = template_list_view.get_entities()
    assert 'Blank' in templates
    assert cirros_image_template_name in templates
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

    template_list_view.select_entity(cirros_image_template_name)
    assert template_list_view.is_new_vm_button_enabled() is True
    assert template_list_view.is_import_button_enabled() is True
    assert template_list_view.is_edit_button_enabled() is True
    assert template_list_view.is_remove_button_enabled() is True
    assert template_list_view.is_export_button_enabled() is True


def test_pools(ovirt_driver):
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    pool_list_view = webadmin_menu.open_pool_list_view()

    pools = pool_list_view.get_entities()
    assert not pools
    assert pool_list_view.is_new_button_enabled() is True
    assert pool_list_view.is_edit_button_enabled() is False
    assert pool_list_view.is_remove_button_enabled() is False


@pytest.fixture
def setup_virtual_machines(engine_api):
    vm_service = test_utils.get_vm_service(engine_api.system_service(), 'vm0')
    if vm_service.get().status == types.VmStatus.DOWN:
        vm_service.start()
        assert assert_utils.equals_within_long(lambda: vm_service.get().status, types.VmStatus.POWERING_UP)


@pytest.fixture
def console_file_helper(console_file_full_path, selenium_artifact_full_path):
    try:
        os.remove(console_file_full_path)
    except FileNotFoundError:
        pass

    yield

    try:
        os.rename(
            console_file_full_path,
            selenium_artifact_full_path('console', 'vv'),
        )
    except FileNotFoundError:
        pass


def test_virtual_machines(
    ansible_storage,
    ovirt_driver,
    setup_virtual_machines,
    save_screenshot,
    console_file_full_path,
    console_file_helper,
    selenium_remote_artifacts_dir,
):
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    vm_list_view = webadmin_menu.open_vm_list_view()

    vms = vm_list_view.get_entities()
    assert 'vm0' in vms
    assert vm_list_view.is_new_button_enabled() is True
    assert vm_list_view.is_edit_button_enabled() is False
    assert vm_list_view.is_shutdown_button_enabled() is False
    assert vm_list_view.is_migrate_button_enabled() is False

    vm_list_view.select_entity('vm0')
    assert vm_list_view.is_new_button_enabled() is True
    assert vm_list_view.is_edit_button_enabled() is True
    assert vm_list_view.is_shutdown_button_enabled() is True
    assert vm_list_view.is_migrate_button_enabled() is True

    vm_list_view.poweroff()
    assert vm_list_view.is_new_button_enabled() is True
    assert vm_list_view.is_edit_button_enabled() is True
    assert vm_list_view.is_shutdown_button_enabled() is False
    assert vm_list_view.is_migrate_button_enabled() is False

    save_screenshot('vms-list-success')

    vm_detail_view = vm_list_view.open_detail_view('vm0')
    assert vm_detail_view.get_name() == 'vm0'
    assert vm_detail_view.get_status() == 'Down'

    run_once_dialog = vm_list_view.run_once()
    run_once_dialog.toggle_console_options()
    run_once_dialog.select_vnc()
    run_once_dialog.run()

    # Waiting for Powering Up instead of Up to speed up the test execution
    vm_detail_view.wait_for_statuses(['Powering Up', 'Up'])
    vm_status = vm_detail_view.get_status()
    assert vm_status == 'Powering Up' or vm_status == 'Up'
    save_screenshot('vms-after-run-once')

    vm_detail_host_devices_tab = vm_detail_view.open_host_devices_tab()
    vm_vgpu_dialog = vm_detail_host_devices_tab.open_manage_vgpu_dialog()

    assert vm_vgpu_dialog.get_title() == 'Manage vGPU'

    vgpu_table_row_1_data = vm_vgpu_dialog.get_row_data(1)
    assert vgpu_table_row_1_data[2] == 'nvidia-11'
    assert vgpu_table_row_1_data[3] == 'GRID M10-2B'
    assert vgpu_table_row_1_data[4] == '2'
    assert vgpu_table_row_1_data[5] == '45'
    assert vgpu_table_row_1_data[6] == '4096x2160'
    assert vgpu_table_row_1_data[7] == '2048M'
    assert vgpu_table_row_1_data[8] == '4'
    assert vgpu_table_row_1_data[9] == '0'

    save_screenshot('vms-vgpu')

    vm_vgpu_dialog.cancel()

    vm_list_view.download_console_file(console_file_full_path, ansible_storage, selenium_remote_artifacts_dir)

    with open(console_file_full_path) as f:
        console_file_text = f.read()
        assert '[virt-viewer]' in console_file_text
        assert '[ovirt]' in console_file_text


def test_storage_domains(ovirt_driver):
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


@pytest.fixture(scope="session")
def image_local_path():
    # Here we can actually use any file that will be available
    # in most situations (on the node containers, on an external grid, etc.)
    # and readable by the 'seluser' user. '/etc/hostname' seems like
    # a safe and reasonable choice.
    return "/etc/hostname"


def test_disks(ovirt_driver, selenium_browser_name, image_local_path):

    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    disks_list_view = webadmin_menu.open_disks_list_view()

    disks = disks_list_view.get_entities()
    assert 'vm0_disk0' in disks
    assert disks_list_view.is_new_button_enabled() is True
    assert disks_list_view.is_edit_button_enabled() is False
    assert disks_list_view.is_remove_button_enabled() is False
    assert disks_list_view.is_move_button_enabled() is False
    assert disks_list_view.is_copy_button_enabled() is False
    assert disks_list_view.is_upload_button_enabled() is True

    disks_list_view.select_entity('vm0_disk0')
    assert disks_list_view.is_new_button_enabled() is True
    assert disks_list_view.is_edit_button_enabled() is True
    assert disks_list_view.is_remove_button_enabled() is True
    assert disks_list_view.is_move_button_enabled() is True
    assert disks_list_view.is_copy_button_enabled() is True
    assert disks_list_view.is_upload_button_enabled() is True

    image_name = "{}-{}".format(selenium_browser_name, int(time.time()))
    disks_list_view.upload(image_local_path, image_name)


def test_dashboard(ovirt_driver):
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    dashboard = webadmin_menu.open_dashboard_view()

    assert dashboard.data_centers_count() is 1
    assert dashboard.clusters_count() is 1
    assert dashboard.hosts_count() is 2
    assert dashboard.storage_domains_count() is 3
    assert dashboard.vm_count() is 5
    assert dashboard.events_count() > 0


def test_logout(ovirt_driver, engine_webadmin_url):
    webadmin_menu = WebAdminTopMenu(ovirt_driver)
    webadmin_menu.wait_for_displayed()
    webadmin_menu.logout()

    webadmin_left_menu = WebAdminLeftMenu(ovirt_driver)
    webadmin_left_menu.wait_for_not_displayed()

    webadmin_top_menu = WebAdminTopMenu(ovirt_driver)
    webadmin_top_menu.wait_for_not_displayed()

    # navigate directly to welcome page to prevent problems with redirecting to login page instead of welcome page
    ovirt_driver.driver.get(engine_webadmin_url)

    welcome_screen = WelcomeScreen(ovirt_driver)
    welcome_screen.wait_for_displayed()
    assert welcome_screen.is_user_logged_out()


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

    # navigate directly to welcome page to prevent problems with redirecting to login page instead of welcome page
    ovirt_driver.driver.get(engine_webadmin_url)

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
):

    ovirt_driver.driver.get(engine_webadmin_url)

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

    grafana.open_dashboard('oVirt Executive Dashboards', '02 Data Center Dashboard')
    assert not grafana.is_error_visible()
    save_screenshot('grafana-dashboard-1')

    grafana.open_dashboard('oVirt Inventory Dashboards', '02 Hosts Inventory Dashboard')
    assert not grafana.is_error_visible()
    save_screenshot('grafana-dashboard-2')
