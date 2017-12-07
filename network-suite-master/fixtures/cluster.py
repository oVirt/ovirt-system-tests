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
import pytest

from lib import clusterlib


@pytest.fixture(scope='session', autouse=True)
def default_cluster(clusters_service):
    DEFAULT_NAME = 'Default'
    cluster = clusterlib.Cluster()
    cluster.import_by_name(DEFAULT_NAME)
    return cluster


@pytest.fixture(scope='session')
def clusters_service(system_service):
    service = system_service.clusters_service()
    clusterlib.Cluster.register(service)
    return service
