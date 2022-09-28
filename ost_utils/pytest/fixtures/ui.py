#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging

import pytest

from selenium import webdriver

from ost_utils.selenium.navigation.driver import Driver
from ost_utils.selenium.page_objects.LoginScreen import LoginScreen


LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def save_screenshot(ovirt_driver, selenium_artifact_full_path):
    def save(description):
        ovirt_driver.save_screenshot(selenium_artifact_full_path(description, 'png'))

    return save


@pytest.fixture(scope="module")
def save_page_source(ovirt_driver, selenium_artifact_full_path):
    def save(description):
        ovirt_driver.save_page_source(selenium_artifact_full_path(description, 'html'))

    return save


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def user_login(ovirt_driver, keycloak_enabled):
    def login(username, password):
        login_screen = LoginScreen(ovirt_driver, keycloak_enabled)
        login_screen.wait_for_displayed()
        login_screen.set_user_name(username)
        login_screen.set_user_password(password)
        login_screen.login()

    return login
