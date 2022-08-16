#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import logging

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from ost_utils import assert_utils

LOGGER = logging.getLogger(__name__)


class Driver:
    def __init__(self, driver):

        # this is a selenium webdriver instance, keeping it private so
        # that we can wrap and control it better (e.g. retry after some exceptions)
        self.__driver = driver

    def get(self, url):
        self.__driver.get(url)

    def quit(self):
        self.__driver.quit()

    def get_capability(self, capability_name):
        return self.__driver.capabilities[capability_name]

    def create_action_chains(self):
        return ActionChains(self.__driver)

    def find_element(self, by, value):
        return self.__driver.find_element(by, value)

    def find_elements(self, by, value):
        return self.__driver.find_elements(by, value)

    def execute_script(self, script):
        return self.__driver.execute_script(script)

    def execute_in_frame(self, xpath, method, *args):
        result = None
        try:
            frame = self.find_element(By.XPATH, xpath)
            self.__driver.switch_to.frame(frame)
            result = method(*args)
        finally:
            self.__driver.switch_to.default_content()
            return result

    def save_screenshot(self, path):
        self.__driver.save_screenshot(path)

    def save_page_source(self, path):
        with open(path, "w", encoding='utf-8') as text_file:
            text_file.write(self.__driver.page_source.encode('utf-8').decode())

    def save_log(self, path, type):
        with open(path, "w", encoding='utf-8') as text_file:
            logs = self.__driver.get_log(type)
            if logs:
                for entry in logs:
                    text_file.write(f'{entry}\n\n')
            else:
                text_file.write('No log entries found')

    def save_console_log(self, path):
        self.save_log(path, 'browser')

    def save_performance_log(self, path):
        self.save_log(path, 'performance')

    def is_id_present(self, idx):
        return self.is_xpath_present(f'//*[@id="{idx}"]')

    def is_class_name_present(self, class_name):
        try:
            self.retry_if_stale(
                # better works for cases with multiple cases
                # than //*[contains(@class, 'class_name')]
                self.find_element,
                By.CLASS_NAME,
                class_name,
            )
            return True
        except NoSuchElementException:
            return False

    def is_xpath_present(self, xpath):
        try:
            self.retry_if_stale(self.find_element, By.XPATH, xpath)
            return True
        except NoSuchElementException:
            return False

    def is_xpath_displayed(self, xpath):
        return self.retry_if_stale(
            lambda: self.is_xpath_present(xpath) and self.find_element(By.XPATH, xpath).is_displayed()
        )

    def is_css_selector_present(self, selector):
        try:
            self.retry_if_stale(self.find_element, By.CSS_SELECTOR, selector)
            return True
        except NoSuchElementException:
            return False

    def is_css_selector_displayed(self, selector):
        return self.retry_if_stale(
            lambda: self.is_css_selector_present(selector)
            and self.find_element(By.CSS_SELECTOR, selector).is_displayed()
        )

    def is_button_enabled(self, text):
        return self.is_xpath_enabled(f'//button[text()="{text}"]')

    def is_xpath_enabled(self, xpath):
        return self.retry_if_stale(lambda: self.find_element(By.XPATH, xpath).is_enabled())

    def xpath_click(self, xpath):
        return self.retry_if_stale(lambda: self.find_element(By.XPATH, xpath).click())

    def id_wait_and_click(self, message, element_id, wait_long=False):
        self.xpath_wait_and_click(message, f'//*[@id="{element_id}"]', wait_long)

    def button_wait_and_click(self, text):
        return self.xpath_wait_and_click(f'Button {text}', f'//button[text()="{text}"]')

    def xpath_wait_and_click(self, message, xpath, wait_long=False):
        wait_until = self.wait_until
        if wait_long:
            wait_until = self.wait_long_until

        wait_until(f'{message} is not displayed', self.is_xpath_displayed, xpath)
        wait_until(f'{message} is not enabled', self.is_xpath_enabled, xpath)
        self.xpath_click(xpath)

    def wait_until(self, message, condition_method, *args):
        self._wait_until(message, assert_utils.SHORT_TIMEOUT, condition_method, *args)

    def wait_long_until(self, message, condition_method, *args):
        self._wait_until(message, assert_utils.LONG_TIMEOUT, condition_method, *args)

    def _wait_until(self, message, timeout, condition_method, *args):
        WebDriverWait(self.__driver, timeout, ignored_exceptions=[TimeoutException]).until(
            ConditionClass(condition_method, *args), message
        )

    def wait_while(self, message, condition_method, *args):
        self._wait_while(message, assert_utils.SHORT_TIMEOUT, condition_method, *args)

    def _wait_while(self, message, timeout, condition_method, *args):
        WebDriverWait(self.__driver, timeout, ignored_exceptions=[TimeoutException]).until_not(
            ConditionClass(condition_method, *args), message
        )

    def retry_if_stale(self, method_to_retry, *args):
        condition = StaleExceptionOccurredCondition(method_to_retry, *args)
        WebDriverWait(self.__driver, assert_utils.LONG_TIMEOUT).until_not(
            condition, 'StaleElementReferenceException occurred'
        )
        if condition.error is not None:
            raise condition.error
        return condition.result


class ConditionClass:
    def __init__(self, condition_method, *args):
        self.condition_method = condition_method
        self.args = args
        self.retry = 0

    def __call__(self, __driver):
        self.retry += 1

        try:
            return self.condition_method(*self.args)
        # Stating it here to avoid logging it
        except NoSuchElementException as e:
            raise e
        except Exception as e:
            LOGGER.exception(f'!!! ConditionClass failed with {e.__class__.__name__} at retry number {self.retry}')
            raise e


class StaleExceptionOccurredCondition:
    def __init__(self, method_to_execute, *args):
        self.method_to_execute = method_to_execute
        self.args = args
        self.result = None
        self.error = None
        self.retry = 0

    def __call__(self, driver):
        should_run_again = False
        try:
            self.retry += 1
            self.result = self.method_to_execute(*self.args)
        # ignore StaleElementReferenceException and try again
        except StaleElementReferenceException:
            should_run_again = True
        # ignore TimeoutException if caused by timeout in java
        except TimeoutException as e:
            LOGGER.exception(
                f'!!! StaleExceptionOccurredCondition failed with {e.__class__.__name__} '
                + f'at retry number {str(self.retry)}'
            )
            if 'java.util.concurrent.TimeoutException' in str(e):
                should_run_again = True
            else:
                self.error = e
        # stating it here just to avoid logging this expected condition or processing it as
        # WebdriverException
        except NoSuchElementException as e:
            self.error = e
        # ignore WebdriverException if caused by the following: Expected to read a START_MAP but instead have: END.
        # Last 0 characters read:
        except WebDriverException as e:
            LOGGER.exception(
                f'!!! StaleExceptionOccurredCondition failed with {e.__class__.__name__} '
                + f'at retry number {self.retry}'
            )
            if 'START_MAP' in str(e):
                should_run_again = True
            else:
                self.error = e
        except Exception as e:
            LOGGER.exception(
                f'!!! StaleExceptionOccurredCondition failed with {e.__class__.__name__} '
                + f'at retry number {self.retry}'
            )

            self.error = e
        return should_run_again
