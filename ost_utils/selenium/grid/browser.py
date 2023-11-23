#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import functools

from selenium import webdriver


@functools.cache
def firefox_options():
    options = webdriver.FirefoxOptions()
    options.set_capability('browserName', 'firefox')
    options.set_capability('acceptInsecureCerts', True)
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1538486
    options.set_capability('moz:useNonSpecCompliantPointerOrigin', True)

    options.set_preference('devtools.console.stdout.content', True)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", "/export")
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/x-virt-viewer")
    return options


@functools.cache
def chrome_options():
    options = webdriver.ChromeOptions()
    options.set_capability('acceptInsecureCerts', True)
    options.set_capability(
        'goog:loggingPrefs',
        {
            'browser': 'ALL',
            'performance': 'ALL',
        },
    )

    prefs = {'download.default_directory': '/export'}
    options.add_experimental_option('prefs', prefs)
    # note: response body is not logged
    options.add_experimental_option('perfLoggingPrefs', {'enableNetwork': True, 'enablePage': True})
    options.add_argument('disable-features=DownloadBubble,DownloadBubbleV2')
    return options
