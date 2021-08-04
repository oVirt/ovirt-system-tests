#
# Copyright 2020-2021 Red Hat, Inc.
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

import pytest


@pytest.fixture(scope="session")
def system_service(engine_api):
    return engine_api.system_service()


@pytest.fixture(scope="session")
def hosts_service(system_service):
    return system_service.hosts_service()


@pytest.fixture(scope="session")
def disks_service(system_service):
    return system_service.disks_service()


@pytest.fixture(scope="session")
def events_service(system_service):
    return system_service.events_service()


@pytest.fixture(scope="session")
def networks_service(system_service):
    return system_service.networks_service()


@pytest.fixture(scope="session")
def storage_domains_service(system_service):
    return system_service.storage_domains_service()


@pytest.fixture(scope="session")
def vms_service(system_service):
    return system_service.vms_service()


@pytest.fixture(scope="session")
def get_vm_service_for_vm(vms_service):
    def service_for(vm_name):
        vms = vms_service.list(search='name={}'.format(vm_name))
        if len(vms) != 1:
            raise RuntimeError("Could not find vm: {}".format(vm_name))
        return vms_service.vm_service(vms[0].id)

    return service_for
