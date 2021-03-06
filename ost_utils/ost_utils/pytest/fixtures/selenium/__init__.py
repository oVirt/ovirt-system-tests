#
# Copyright 2020 Red Hat, Inc.
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

import pytest

import ost_utils.os_utils as os_utils
import ost_utils.selenium.grid.docker as docker
import ost_utils.selenium.grid.podman as podman

from ost_utils.pytest.fixtures.engine import engine_fqdn
from ost_utils.pytest.fixtures.engine import engine_ip


def _has_podman():
    return os.system("podman --version &> /dev/null") == 0


def _has_docker():
    return os.system("docker -v &> /dev/null") == 0


def _grid_backend():
    env_backend = os.environ.get("OST_CONTAINER_BACKEND", None)
    if env_backend in ("docker", "podman"):
        return env_backend

    if _has_podman():
        return "podman"

    if _has_docker():
        return "docker"


def _env_hub_url():
    return os.environ.get("OST_SELENIUM_HUB_URL", None)


@pytest.fixture(scope="session")
def hub_url(engine_fqdn, engine_ip):
    env_url = _env_hub_url()

    if env_url is not None:
        yield env_url
    else:
        backend = _grid_backend()
        if backend == "podman":
            if os_utils.on_centos(8) and os_utils.inside_mock():
                pytest.skip("podman doesn't work in mock")
            with podman.grid(engine_fqdn, engine_ip) as hub_url:
                yield hub_url
        elif backend == "docker":
            with docker.grid(engine_fqdn, engine_ip) as hub_url:
                yield hub_url
        else:
            raise RuntimeError("No container backend available to set up the grid")
