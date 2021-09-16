#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import logging

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.support.ui import WebDriverWait

from ost_utils import assertions

LOGGER = logging.getLogger(__name__)


class Driver:
    def __init__(self, driver):

        # this is a selenium webdriver instance
        self.driver = driver

    def execute_in_frame(self, xpath, method, *args):
        result = None
        try:
            frame = self.driver.find_element_by_xpath(xpath)
            self.driver.switch_to.frame(frame)
            result = method(*args)
        finally:
            self.driver.switch_to.default_content()
            return result

    def save_screenshot(self, path):
        self.driver.save_screenshot(path)

    def save_page_source(self, path):
        with open(path, "w") as text_file:
            text_file.write(self.driver.page_source.encode('utf-8').decode())

    def save_console_log(self, path):
        with open(path, "w") as text_file:
            logs = self.driver.get_log('browser')
            if logs:
                for entry in logs:
                    text_file.write(f'{entry}\n\n')
            else:
                text_file.write('No console log entries found')

    def is_id_present(self, idx):
        return self.is_xpath_present(f'//*[@id="{idx}"]')

    def is_class_name_present(self, class_name):
        try:
            self.retry_if_stale(
                # better works for cases with multiple cases
                # than //*[contains(@class, 'class_name')]
                self.driver.find_element_by_class_name,
                class_name,
            )
            return True
        except NoSuchElementException:
            return False

    def is_xpath_present(self, xpath):
        try:
            self.retry_if_stale(self.driver.find_element_by_xpath, xpath)
            return True
        except NoSuchElementException:
            return False

    def is_xpath_displayed(self, xpath):
        return self.retry_if_stale(
            lambda: self.is_xpath_present(xpath)
            and self.driver.find_element_by_xpath(xpath).is_displayed()
        )

    def is_button_enabled(self, text):
        return self.is_xpath_enabled(f'//button[text()="{text}"]')

    def is_xpath_enabled(self, xpath):
        return self.retry_if_stale(
            lambda: self.driver.find_element_by_xpath(xpath).is_enabled()
        )

    def xpath_click(self, xpath):
        return self.retry_if_stale(
            lambda: self.driver.find_element_by_xpath(xpath).click()
        )

    def id_wait_and_click(self, message, element_id, wait_long=False):
        self.xpath_wait_and_click(
            message, f'//*[@id="{element_id}"]', wait_long
        )

    def button_wait_and_click(self, text):
        return self.xpath_wait_and_click(
            f'Button {text}', f'//button[text()="{text}"]'
        )

    def xpath_wait_and_click(self, message, xpath, wait_long=False):
        wait_until = self.wait_until
        if wait_long:
            wait_until = self.wait_long_until

        wait_until(
            f'{message} is not displayed', self.is_xpath_displayed, xpath
        )
        wait_until(f'{message} is not enabled', self.is_xpath_enabled, xpath)
        self.xpath_click(xpath)

    def wait_until(self, message, condition_method, *args):
        self._wait_until(
            message, assertions.SHORT_TIMEOUT, condition_method, *args
        )

    def wait_long_until(self, message, condition_method, *args):
        self._wait_until(
            message, assertions.LONG_TIMEOUT, condition_method, *args
        )

    def _wait_until(self, message, timeout, condition_method, *args):
        WebDriverWait(self.driver, timeout).until(
            ConditionClass(condition_method, *args), message
        )

    def wait_while(self, message, condition_method, *args):
        self._wait_while(
            message, assertions.SHORT_TIMEOUT, condition_method, *args
        )

    def wait_long_while(self, message, condition_method, *args):
        self._wait_while(
            message, assertions.LONG_TIMEOUT, condition_method, *args
        )

    def _wait_while(self, message, timeout, condition_method, *args):
        WebDriverWait(self.driver, timeout).until_not(
            ConditionClass(condition_method, *args), message
        )

    def retry_if_stale(self, method_to_retry, *args):
        condition = StaleExceptionOccurredCondition(method_to_retry, *args)
        WebDriverWait(self.driver, assertions.LONG_TIMEOUT).until_not(
            condition, 'StaleElementReferenceException occurred'
        )
        if condition.error is not None:
            raise condition.error
        return condition.result


class ConditionClass:
    def __init__(self, condition_method, *args):
        self.condition_method = condition_method
        self.args = args

    def __call__(self, driver):
        return self.condition_method(*self.args)


class StaleExceptionOccurredCondition:
    def __init__(self, method_to_execute, *args):
        self.method_to_execute = method_to_execute
        self.args = args
        self.result = None
        self.error = None

    def __call__(self, driver):
        try:
            self.result = self.method_to_execute(*self.args)
            return False
        # ignore StaleElementReferenceException and try again
        except StaleElementReferenceException:
            return True
        # throw any other exception, even NoSuchElementException ignored
        # by WebDriverWait by default
        except Exception as e:
            self.error = e
            return False
