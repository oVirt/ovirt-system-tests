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

import os
import time

from selenium import webdriver
from selenium.common.exceptions import (ElementNotVisibleException,
                                        NoSuchElementException,
                                        WebDriverException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..selenium_constants import *

DEBUG = False


class DriverException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Driver(object):

    def __init__(self, driver):

        # this is a selenium webdriver instance
        self.driver = driver

    def wait_for_id(self, text):

        elem = None

        for x in range(1, DRIVER_MAX_RETRIES):
            try:
                if DEBUG:
                    print("self.driver.find_element_by_id(%s)" % text)
                elem = self.driver.find_element_by_id(text)
                break
            except (NoSuchElementException, WebDriverException, ElementNotVisibleException) as e:
                time.sleep(DRIVER_SLEEP_TIME)

        if elem is None:
            self.driver.save_screenshot('%s could not locate by id %s.png' % (time.time(), text))
            print("could not locate by id: " + text)
            raise DriverException("could not locate by id: " + text)

        return elem

    def action_on_element(self, text, action, path=None):
        elem = None
        find_by = 'id'

        for x in range(1, DRIVER_MAX_RETRIES):
            try:
                if DEBUG:
                    print("self.driver.find_element_by_id(%s)" % text)
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
            print("could not locate by text: " + text)
            raise DriverException("could not locate by text: " + text)
        return elem

    def id_click(self, id):

        try:
            for x in range(1, DRIVER_MAX_RETRIES):

                # try to find the element. That requires its own wait loop, so it lives
                # in another method for clarity
                if DEBUG:
                    print("self.wait_for_id(%s)" % id)

                ret = self.wait_for_id(id)

                try:
                    # try to click it. This may or may not work, hence the surrounding wait loop
                    if DEBUG:
                        print("" + str(ret) + ".click()")

                    ret.click()
                    break
                except (NoSuchElementException, WebDriverException, ElementNotVisibleException) as e:
                    time.sleep(DRIVER_SLEEP_TIME)

        except DriverException as e:
            self.driver.save_screenshot('%s id_click couldnt find element %s.png' % (time.time(), id))
            print('id_click couldnt find element %s' % id)
            raise

    def hover_to_id(self, id):

        try:
            for x in range(1, DRIVER_MAX_RETRIES):

                # try to find the element. That requires its own wait loop, so it lives
                # in another method for clarity
                if DEBUG:
                    print("self.wait_for_id(%s)" % id)

                ret = self.wait_for_id(id)

                try:
                    # try to hover over it. This may or may not work, hence the surrounding wait loop
                    if DEBUG:
                        print("hover.perform() on %s" % ret)

                    hover = ActionChains(self.driver).move_to_element(ret)
                    hover.perform()
                    time.sleep(LEFT_NAV_HOVER_TIME)
                    break

                except (NoSuchElementException, WebDriverException, ElementNotVisibleException) as e:
                    time.sleep(DRIVER_SLEEP_TIME)

        except DriverException as e:
            self.driver.save_screenshot('%s hover_to_id couldnt find element %s.png' % (time.time(), id))
            print('hover_to_id couldnt find element %s' % id)
            raise

    def safe_close_dialog(self):

        try:
            dialog_close_button = self.driver.find_element_by_css_selector('.modal-header .close')
            if dialog_close_button:
                dialog_close_button.click()
                if DEBUG:
                    print("force closed a dialog")
        except NoSuchElementException as e:
            pass

    def shutdown(self):
        self.driver.quit()

    def refresh(self):
        self.driver.refresh()

    def save_screenshot(self, path, delay=0):
        if delay > 0 and delay <= 10:
            time.sleep(delay)

        print("saving screenshot " + path)
        self.driver.save_screenshot(path)
