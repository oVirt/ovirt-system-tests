#
# Copyright 2015-2017 Red Hat, Inc.
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
import warnings
import logging
import yaml
from collections import OrderedDict
from sh import vagrant

import sdk_utils
from vm import VM
import constants
import testlib


from sdk_utils import partial, available_sdks, require_sdk

import ovirtsdk.api
from ovirtsdk.infrastructure.errors import (RequestError, ConnectionError)


LOGGER = logging.getLogger(__name__)

try:
    import ovirtsdk4 as sdk4
    import ovirtsdk4.types as otypes
except ImportError:
    pass


class EngineVM(VM):
    def __init__(self, *args, **kwargs):
        super(EngineVM, self).__init__(*args, **kwargs)
        self._api_v3 = None
        self._api_v4 = None

    def stop(self):
        super(EngineVM, self).stop()
        self._api_v3 = None


    def _artifact_paths(self):
        inherited_artifacts = super(EngineVM, self)._artifact_paths()
        return set(inherited_artifacts + ['/var/log'])

    def _create_api(self, api_ver):
        url = 'https://%s/ovirt-engine/api' % self.ip()
        if api_ver == 3:
            if '3' not in available_sdks():
                raise RuntimeError('oVirt Python SDK v3 not found.')
            return ovirtsdk.api.API(
                url=url,
                username=constants.ENGINE_USER,
                password=str(constants.ENGINE_PASSWORD),
                validate_cert_chain=False,
                insecure=True,
            )
        if api_ver == 4:
            if '4' not in available_sdks():
                raise RuntimeError('oVirt Python SDK v4 not found.')
            return sdk4.Connection(
                url=url,
                username=constants.ENGINE_USER,
                password=str(constants.ENGINE_PASSWORD),
                insecure=True,
                debug=True,
            )
        raise RuntimeError('Unknown API requested: %s' % api_ver)

    def _get_api(self, api_ver):
        try:
            api_v3 = []
            api_v4 = []

            def get():
                instance = self._create_api(api_ver)
                if instance:
                    if api_ver == 3:
                        api_v3.append(instance)
                    else:
                        api_v4.append(instance)
                    return True
                return False

            testlib.assert_true_within_short(
                get,
                allowed_exceptions=[RequestError, ConnectionError],
            )
        except AssertionError:
            raise RuntimeError('Failed to connect to the engine')

        if api_ver == 3:
            return api_v3.pop()
        else:
            testapi = api_v4.pop()
            counter = 1
            while not testapi.test():
                if counter == 20:
                    raise RuntimeError('test api call failed')
                else:
                    time.sleep(3)
                    counter += 1

            return testapi

    def get_api(self, api_ver=3):
        if api_ver == 3:
            return self.get_api_v3()
        if api_ver == 4:
            return self.get_api_v4()

    def get_api_v3(self):
        if self._api_v3 is None or not self._api_v3.test():
            self._api_v3 = self._get_api(api_ver=3)
        return self._api_v3

    def get_api_v4(self, check=False):
        if self._api_v4 is None or not self._api_v4.test():
            self._api_v4 = self._get_api(api_ver=4)
            if check and self._api_v4 is None:
                raise RuntimeError('Could not connect to engine')
        return self._api_v4

    def get_api_v4_system_service(self):
        api = self.get_api_v4(False)
        return api.system_service()


    @require_sdk(version='4')
    def status(self):
        api = self.get_api_v4(check=True)
        sys_service = api.system_service().get()
        info = {'global': {}, 'items': {}}

        info['global']['version'
                       ] = sys_service.product_info.version.full_version
        info['global']['web_ui'] = OrderedDict(
            [
                ('url', self.ip()), ('username', constants.ENGINE_USER),
                ('password', self.metadata['ovirt-engine-password'])
            ]
        )

        for k, v in vars(sys_service.summary).viewitems():
            if isinstance(v, otypes.ApiSummaryItem):
                info['items'][k.lstrip('_')] = OrderedDict(
                    [
                        ('total', v.total),
                        ('active', v.active),
                    ]
                )

        return info


class HostVM(VM):
    def _artifact_paths(self):
        inherited_artifacts = super(HostVM, self)._artifact_paths()
        return set(inherited_artifacts + [
            '/var/log',
        ])


class HEHostVM(HostVM):
    def _artifact_paths(self):
        inherited_artifacts = super(HEHostVM, self)._artifact_paths()
        return set(inherited_artifacts)
