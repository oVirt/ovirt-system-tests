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
import logging
import time

from ost_utils import assertions

from selenium.common.exceptions import (ElementNotVisibleException,
                                        NoSuchElementException,
                                        WebDriverException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

DEBUG = False

LOGGER = logging.getLogger(__name__)

DRIVER_MAX_RETRIES = 200
DRIVER_SLEEP_TIME = .12


class DriverException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Driver:

    def __init__(self, driver):

        # this is a selenium webdriver instance
        self.driver = driver

    def wait_for_id(self, text):

        elem = None

        for x in range(1, DRIVER_MAX_RETRIES):
            try:
                if DEBUG:
                    LOGGER.debug("self.driver.find_element_by_id(%s)" % text)
                elem = self.driver.find_element_by_id(text)
                break
            except (NoSuchElementException, WebDriverException, ElementNotVisibleException) as e:
                time.sleep(DRIVER_SLEEP_TIME)

        if elem is None:
            self.driver.save_screenshot('%s could not locate by id %s.png' % (time.time(), text))
            LOGGER.debug("could not locate by id: " + text)
            raise DriverException("could not locate by id: " + text)

        return elem

    def action_on_element(self, text, action, path=None):
        elem = None
        find_by = 'id'

        for x in range(1, DRIVER_MAX_RETRIES):
            try:
                if DEBUG:
                    LOGGER.debug("self.driver.find_element_by_id(%s)" % text)
                elif action == 'click':
                    elem = self.driver.find_element_by_link_text(text)
                    elem.click()
                    find_by = 'text'
                elif action == 'send':
                    elem = self.driver.find_element_by_id(text)
                    elem.send_keys(path)
                break
            except (NoSuchElementException, WebDriverException, ElementNotVisibleException) as e:
                time.sleep(DRIVER_SLEEP_TIME)

        if elem is None:
            self.driver.save_screenshot('%s could not locate by %s %s.png' % (time.time(), find_by, text))
            LOGGER.debug("could not locate by text: " + text)
            raise DriverException("could not locate by text: " + text)
        return elem

    def id_click(self, id):

        try:
            for x in range(1, DRIVER_MAX_RETRIES):

                # try to find the element. That requires its own wait loop, so it lives
                # in another method for clarity
                if DEBUG:
                    LOGGER.debug("self.wait_for_id(%s)" % id)

                ret = self.wait_for_id(id)

                try:
                    # try to click it. This may or may not work, hence the surrounding wait loop
                    if DEBUG:
                        LOGGER.debug("" + str(ret) + ".click()")

                    ret.click()
                    break
                except (NoSuchElementException, WebDriverException, ElementNotVisibleException) as e:
                    time.sleep(DRIVER_SLEEP_TIME)

        except DriverException as e:
            self.driver.save_screenshot('%s id_click couldnt find element %s.png' % (time.time(), id))
            LOGGER.debug('id_click couldnt find element %s' % id)
            raise

    def hover_to_id(self, id):

        try:
            for x in range(1, DRIVER_MAX_RETRIES):

                # try to find the element. That requires its own wait loop, so it lives
                # in another method for clarity
                if DEBUG:
                    LOGGER.debug("self.wait_for_id(%s)" % id)

                ret = self.wait_for_id(id)

                try:
                    # try to hover over it. This may or may not work, hence the surrounding wait loop
                    if DEBUG:
                        LOGGER.debug("hover.perform() on %s" % ret)

                    hover = ActionChains(self.driver).move_to_element(ret)
                    hover.perform()
                    time.sleep(DRIVER_SLEEP_TIME)
                    break

                except (NoSuchElementException, WebDriverException, ElementNotVisibleException) as e:
                    time.sleep(DRIVER_SLEEP_TIME)

        except DriverException as e:
            self.driver.save_screenshot('%s hover_to_id couldnt find element %s.png' % (time.time(), id))
            LOGGER.debug('hover_to_id couldnt find element %s' % id)
            raise

    def retry_if_stale(self, method_to_retry, *args):
        success = False
        return_value = None
        exception = None

        for x in range(1, DRIVER_MAX_RETRIES):
            try:
                if DEBUG:
                    LOGGER.debug("self.driver.retry_if_stale(%s)" % method_to_retry)

                return_value = method_to_retry(*args)
                success = True
                break
            except StaleElementReferenceException as e:
                time.sleep(DRIVER_SLEEP_TIME)
                exception = e

        if not success:
            self.save_screenshot("stale-element")
            LOGGER.debug("StaleElementReferenceException occurred max times, stop retrying")
            raise exception

        return return_value

    def execute_in_frame(self, xpath, method, *args):
        result = None
        try:
            frame = self.driver.find_element_by_xpath(xpath)
            self.driver.switch_to.frame(frame)
            result = method(*args)
        finally:
            self.driver.switch_to.default_content()
            return result

    def safe_close_dialog(self):

        try:
            dialog_close_button = self.driver.find_element_by_css_selector('.modal-header .close')
            if dialog_close_button:
                dialog_close_button.click()
                if DEBUG:
                    LOGGER.debug("force closed a dialog")
        except NoSuchElementException as e:
            pass

    def shutdown(self):
        self.driver.quit()

    def refresh(self):
        self.driver.refresh()

    def save_screenshot(self, path, delay=0):
        if delay > 0 and delay <= 10:
            time.sleep(delay)

        self.driver.save_screenshot(path)

    def save_page_source(self, path, delay=0):
        if delay > 0 and delay <= 10:
            time.sleep(delay)

        with open(path, "w") as text_file:
            text_file.write(self.driver.page_source.encode('utf-8').decode())

    def id_wait_and_click(self, message, element_id, wait_long=False):
        self.xpath_wait_and_click(message, '//*[@id="' + element_id + '"]', wait_long)

    def is_id_present(self, idx):
        try:
            self.driver.find_element_by_id(idx)
            return True
        except NoSuchElementException:
            return False

    def is_class_name_present(self, class_name):
        try:
            self.driver.find_element_by_class_name(class_name)
            return True
        except NoSuchElementException:
            return False

    def button_wait_and_click(self, text):
        return self.xpath_wait_and_click('Button ' + text, '//button[text()="' + text + '"]')

    def is_button_displayed(self, text):
        return self.is_xpath_displayed('//button[text()="' + text + '"]')

    def is_button_enabled(self, text):
        return self.is_xpath_enabled('//button[text()="' + text + '"]')

    def button_click(self, xpath):
        self.xpath_click('//button[text()="' + xpath + '"]')

    def is_xpath_present(self, xpath):
        try:
            self.retry_if_stale(
                self.driver.find_element_by_xpath,
                xpath
                )
            return True
        except NoSuchElementException:
            return False

    def is_xpath_displayed(self, xpath):
        return self.retry_if_stale(
            self._is_xpath_displayed,
            xpath
            )

    def _is_xpath_displayed(self, xpath):
        return self.driver.find_element_by_xpath(xpath).is_displayed()

    def is_xpath_enabled(self, xpath):
        return self.retry_if_stale(
            self._is_xpath_enabled,
            xpath
            )

    def _is_xpath_enabled(self, xpath):
        return self.driver.find_element_by_xpath(xpath).is_enabled()

    def xpath_click(self, xpath):
        return self.retry_if_stale(
            self._xpath_click,
            xpath
            )

    def _xpath_click(self, xpath):
        self.driver.find_element_by_xpath(xpath).click()

    def xpath_wait_and_click(self, message, xpath, wait_long=False):
        wait_until = self.wait_until
        if wait_long:
            wait_until = self.wait_long_until

        wait_until(message + ' is not displayed', self.is_xpath_displayed, xpath)
        wait_until(message + ' is not enabled', self.is_xpath_enabled, xpath)
        self.xpath_click(xpath)

    def wait_until(self, message, condition_method, *args):
        self._wait_until(message, assertions.SHORT_TIMEOUT, condition_method, *args)

    def wait_long_until(self, message, condition_method, *args):
        self._wait_until(message, assertions.LONG_TIMEOUT, condition_method, *args)

    def _wait_until(self, message, timeout, condition_method, *args):
        WebDriverWait(self.driver, timeout).until(ConditionClass(condition_method, *args), message)

    def wait_while(self, message, condition_method, *args):
        self._wait_while(message, assertions.SHORT_TIMEOUT, condition_method, *args)

    def wait_long_while(self, message, condition_method, *args):
        self._wait_while(message, assertions.LONG_TIMEOUT, condition_method, *args)

    def _wait_while(self, message, timeout, condition_method, *args):
        WebDriverWait(self.driver, timeout).until_not(ConditionClass(condition_method, *args), message)

class ConditionClass:
    def __init__(self, condition_method, *args):
        self.condition_method = condition_method
        self.args = args

    def __call__(self, driver):
        return self.condition_method(*self.args)
