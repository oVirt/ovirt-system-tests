#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from __future__ import absolute_import
from __future__ import print_function

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
from ost_utils import constants
from ost_utils.constants import *
from ost_utils.pytest.fixtures.ansible import ansible_host0_facts
from ost_utils.pytest.fixtures.ansible import ansible_host1_facts
from ost_utils.pytest.fixtures.artifacts import artifacts_dir
from ost_utils.pytest.fixtures.selenium import *
from ost_utils.pytest.fixtures.virt import cirros_image_template_name
from ost_utils.selenium.navigation.driver import Driver
from ost_utils.selenium.page_objects.ClusterListView import ClusterListView
from ost_utils.selenium.page_objects.WelcomeScreen import WelcomeScreen
from ost_utils.selenium.page_objects.LoginScreen import LoginScreen
from ost_utils.selenium.page_objects.WebAdminLeftMenu import WebAdminLeftMenu
from ost_utils.selenium.page_objects.WebAdminTopMenu import WebAdminTopMenu
from ost_utils.selenium.page_objects.VmListView import VmListView
from ost_utils.selenium.page_objects.VmPortal import VmPortal
from ost_utils.selenium.page_objects.GrafanaLoginScreen import (
    GrafanaLoginScreen,
)
from ost_utils.selenium.page_objects.Grafana import Grafana
from ost_utils.shell import ShellError
from ost_utils.shell import shell


LOGGER = logging.getLogger(__name__)


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


@pytest.fixture(scope="session")
def ovirt_driver(
    engine_webadmin_url, selenium_browser_options, selenium_grid_url, selenium_screen_width, selenium_screen_height
):
    driver = None
    exception = None
    for i in range(5):
        try:
            driver = webdriver.Remote(command_executor=selenium_grid_url, options=selenium_browser_options)
            break
        except Exception as e:
            LOGGER.exception(f'Failed to create driver {i}')
            exception = e
    else:
        LOGGER.error('Failed to create the selenium webdriver after 5 retries')
        raise exception

    ovirt_driver = Driver(driver)
    ovirt_driver.set_window_size(selenium_screen_width, selenium_screen_height)
    ovirt_driver.get(engine_webadmin_url)

    try:
        yield ovirt_driver
    finally:
        ovirt_driver.quit()


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
        if ovirt_driver.get_capability('browserName') == 'chrome':
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


def test_clusters(ovirt_driver, save_screenshot, selenium_browser_name, ost_cluster_name):
    cluster_description = f'Cluster description for {selenium_browser_name}'

    # Open cluster list view
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    cluster_list_view = webadmin_menu.open_cluster_list_view()
    save_screenshot('cluster-list-view')

    # Test cluster list view
    clusters = cluster_list_view.get_entities()
    assert ost_cluster_name in clusters

    cluster_list_view.select_entity(ost_cluster_name)
    assert cluster_list_view.is_new_button_enabled() is True
    assert cluster_list_view.is_edit_button_enabled() is True
    assert cluster_list_view.is_upgrade_button_enabled() is True

    # Edit cluster using dialog
    cluster_dialog = cluster_list_view.edit(ost_cluster_name)
    cluster_dialog.setDescription(cluster_description)
    save_screenshot('cluster-edit-dialog')
    cluster_dialog.ok()

    # Test the edited value in the details view
    cluster_list_view.wait_for_displayed()
    cluster_detail_view = cluster_list_view.open_detail_view(ost_cluster_name)
    assert cluster_detail_view.get_name() == ost_cluster_name
    assert cluster_detail_view.get_description() == cluster_description


def test_cluster_upgrade(
    ovirt_driver, engine_api, save_screenshot, ost_cluster_name, ansible_host0_facts, ansible_host1_facts
):
    host0_name = ansible_host0_facts.get("ansible_hostname")
    host1_name = ansible_host1_facts.get("ansible_hostname")
    cluster_service = test_utils.get_cluster_service(engine_api.system_service(), ost_cluster_name)
    original_schedulling_policy_id = cluster_service.get().scheduling_policy.id
    cluster_maintenance_schedulling_policy_id = '7677771e-5eab-422e-83fa-dc04080d21b7'

    # cluster is not set to cluster_maintenance policy yet
    assert original_schedulling_policy_id != cluster_maintenance_schedulling_policy_id

    cluster_list_view = ClusterListView(ovirt_driver)
    upgrade_dialog = cluster_list_view.upgrade(ost_cluster_name)

    upgrade_dialog.toggle_check_all_hosts()
    save_screenshot('cluster-upgrade-dialog-select-hosts')
    upgrade_dialog.next()

    upgrade_dialog.toggle_check_for_upgrade()
    upgrade_dialog.toggle_reboot_hosts()
    save_screenshot('cluster-upgrade-dialog-options')
    upgrade_dialog.next()

    save_screenshot('cluster-upgrade-dialog-review')
    upgrade_dialog.upgrade()

    save_screenshot('cluster-upgrade-dialog-progress')

    events_view = upgrade_dialog.go_to_event_log()
    assert assert_utils.true_within_short(lambda: events_view.events_contain('Cluster upgrade progress: 0%'))
    assert assert_utils.true_within_short(lambda: events_view.events_contain('Successfully set upgrade running flag'))

    # cluster is set to cluster_maintenance policy
    assert assert_utils.true_within_short(
        lambda: cluster_service.get().scheduling_policy.id == cluster_maintenance_schedulling_policy_id
    )

    # there could be two messages - "Check for update" or "Update" for the host depending on
    # whether there are updates available and if the updates have been retrieved before
    assert assert_utils.true_within_short(lambda: events_view.events_contain(f'update of host {host0_name}'))
    assert assert_utils.true_within_short(lambda: events_view.events_contain(f'update of host {host1_name}'))
    assert assert_utils.true_within_short(
        lambda: events_view.events_contain(f'Upgrade of cluster {ost_cluster_name} finished successfully')
    )
    assert assert_utils.true_within_short(lambda: events_view.events_contain('Cluster upgrade progress: 100%'))
    assert assert_utils.true_within_short(
        lambda: events_view.events_contain('Successfully cleared upgrade running flag')
    )

    # cluster is set to the original policy
    assert assert_utils.true_within_short(
        lambda: cluster_service.get().scheduling_policy.id == original_schedulling_policy_id
    )


def test_hosts(ovirt_driver, ansible_host0_facts, save_screenshot, selenium_browser_name):
    host_name = ansible_host0_facts.get("ansible_hostname")
    host_comment = f'Host comment for {selenium_browser_name}'

    # Open host list view
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    host_list_view = webadmin_menu.open_host_list_view()
    save_screenshot('host-list-view')

    # Test host list view
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

    # Edit host using dialog
    host_dialog = host_list_view.edit(host_name)
    host_dialog.set_comment(host_comment)
    host_dialog.ok()

    host_list_view.wait_for_displayed()
    host_dialog = host_list_view.edit(host_name)
    save_screenshot('host-edit-dialog')
    assert host_dialog.get_comment() == host_comment
    host_dialog.cancel()

    # Test the hostname in the details view
    host_list_view.wait_for_displayed()
    host_detail_view = host_list_view.open_detail_view(host_name)
    assert host_detail_view.get_hostname() == host_name


def test_templates(ovirt_driver, cirros_image_template_name, save_screenshot, selenium_browser_name):
    blank_template_name = 'Blank'
    blank_template_description = f'Blank template description for {selenium_browser_name}'
    imported_template = 'imported_temp'
    imported_template_description = f'Imported template description for {selenium_browser_name}'

    # Open template list view
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    template_list_view = webadmin_menu.open_template_list_view()
    save_screenshot('host-list-view')

    # Test templates list view
    templates = template_list_view.get_entities()
    assert blank_template_name in templates
    assert cirros_image_template_name in templates
    assert imported_template in templates
    assert template_list_view.is_new_vm_button_enabled() is False
    assert template_list_view.is_import_button_enabled() is True
    assert template_list_view.is_edit_button_enabled() is False
    assert template_list_view.is_remove_button_enabled() is False
    assert template_list_view.is_export_button_enabled() is False

    template_list_view.select_entity(blank_template_name)
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

    # Edit templates using dialog
    template_dialog = template_list_view.edit(blank_template_name)
    template_dialog.setDescription(blank_template_description)
    save_screenshot('blank-template-edit-dialog')
    template_dialog.ok()

    template_list_view.wait_for_displayed()
    template_dialog = template_list_view.edit(imported_template)
    template_dialog.setDescription(imported_template_description)
    save_screenshot('imported-template-edit-dialog')
    template_dialog.ok()

    # Test the edited values in the details view
    template_list_view.wait_for_displayed()
    template_detail_view = template_list_view.open_detail_view(blank_template_name)
    save_screenshot('blank-template-detail')
    assert template_detail_view.get_name() == blank_template_name
    assert template_detail_view.get_description() == blank_template_description

    webadmin_menu.open_template_list_view()
    template_detail_view = template_list_view.open_detail_view(imported_template)
    assert template_detail_view.get_name() == imported_template
    assert template_detail_view.get_description() == imported_template_description


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
    vm_name = 'vm0'
    vm_description = f'VM description for {selenium_browser_name}'

    # Open VM list view
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    vm_list_view = webadmin_menu.open_vm_list_view()
    save_screenshot('vm-list-view')

    # Test VM list view
    vms = vm_list_view.get_entities()
    assert vm_name in vms
    assert vm_list_view.is_new_button_enabled() is True
    assert vm_list_view.is_edit_button_enabled() is False
    assert vm_list_view.is_shutdown_button_enabled() is False
    assert vm_list_view.is_migrate_button_enabled() is False

    vm_list_view.select_entity(vm_name)
    assert vm_list_view.is_new_button_enabled() is True
    assert vm_list_view.is_edit_button_enabled() is True
    assert vm_list_view.is_shutdown_button_enabled() is True
    assert vm_list_view.is_migrate_button_enabled() is True

    vm_list_view.poweroff()
    assert vm_list_view.is_new_button_enabled() is True
    assert vm_list_view.is_edit_button_enabled() is True
    assert vm_list_view.is_shutdown_button_enabled() is False
    assert vm_list_view.is_migrate_button_enabled() is False

    # Edit VM using dialog
    vm_dialog = vm_list_view.edit(vm_name)
    vm_dialog.setDescription(vm_description)
    save_screenshot('vm-edit-dialog')
    vm_dialog.ok()

    # Test the VM details view
    vm_list_view.wait_for_displayed()
    vm_detail_view = vm_list_view.open_detail_view(vm_name)
    save_screenshot('vm-detail')
    assert vm_detail_view.get_name() == vm_name
    assert vm_detail_view.get_description() == vm_description
    assert vm_detail_view.get_status() == 'Down'

    # Test Run Once
    run_once_dialog = vm_list_view.run_once()
    run_once_dialog.toggle_console_options()
    run_once_dialog.select_vnc()
    run_once_dialog.run()

    # Waiting for Powering Up instead of Up to speed up the test execution
    vm_detail_view.wait_for_statuses(['Powering Up', 'Up'])
    vm_status = vm_detail_view.get_status()
    save_screenshot('vms-after-run-once')
    assert vm_status == 'Powering Up' or vm_status == 'Up'

    # Test Manage VGPU dialog
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

    # Teste console file download
    vm_list_view.download_console_file(console_file_full_path, ansible_storage, selenium_remote_artifacts_dir)

    with open(console_file_full_path) as f:
        console_file_text = f.read()
        assert '[virt-viewer]' in console_file_text
        assert '[ovirt]' in console_file_text


def test_make_template(
    ansible_storage,
    ovirt_driver,
    selenium_browser_name,
    save_screenshot,
    console_file_full_path,
    console_file_helper,
    selenium_remote_artifacts_dir,
):
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    vm_list_view = webadmin_menu.open_vm_list_view()

    template_name = f'{selenium_browser_name}_{int(time.time())}'

    vm_list_view = VmListView(ovirt_driver)
    vm_list_view.select_entity('vm1')
    template_dialog = vm_list_view.new_template()
    save_screenshot('new-template-dialog')
    template_dialog.set_name_and_ok(template_name)

    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    template_list_view = webadmin_menu.open_template_list_view()
    templates = template_list_view.get_entities()
    assert template_name in templates
    assert assert_utils.equals_within_short(lambda: template_list_view.get_status(template_name), 'OK')


def test_storage_domains(ovirt_driver):
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    storage_domain_list_view = webadmin_menu.open_storage_domain_list_view()

    domains = storage_domain_list_view.get_entities()
    assert constants.SD_NFS_NAME in domains
    assert storage_domain_list_view.is_new_button_enabled() is True
    assert storage_domain_list_view.is_import_button_enabled() is True
    assert storage_domain_list_view.is_manage_button_enabled() is False
    assert storage_domain_list_view.is_remove_button_enabled() is False

    storage_domain_list_view.select_entity(constants.SD_NFS_NAME)
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
    assert assert_utils.equals_within_short(lambda: disks_list_view.get_status(image_name), 'OK')


def test_dashboard(ovirt_driver):
    webadmin_menu = WebAdminLeftMenu(ovirt_driver)
    dashboard = webadmin_menu.open_dashboard_view()

    assert dashboard.data_centers_count() is 1
    assert dashboard.clusters_count() is 1
    assert dashboard.hosts_count() is 2
    assert dashboard.storage_domains_count() is 3
    assert dashboard.vm_count() is 5
    assert dashboard.events_count() > 0


def test_logout(ovirt_driver, engine_webadmin_url, keycloak_enabled):
    webadmin_menu = WebAdminTopMenu(ovirt_driver)
    webadmin_menu.wait_for_displayed()
    webadmin_menu.logout()

    # navigate directly to welcome page to prevent problems with redirecting to login page instead of welcome page
    ovirt_driver.get(engine_webadmin_url)

    welcome_screen = WelcomeScreen(ovirt_driver)
    welcome_screen.wait_for_displayed()
    welcome_screen.wait_for_user_logged_out()
    assert welcome_screen.is_user_logged_out()

    if keycloak_enabled:
        # delete all cookies to workaround not logging out from the Keycloak properly
        ovirt_driver.delete_all_cookies()


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
