#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import os

import pytest

import ost_utils.os_utils as os_utils
import ost_utils.selenium.grid.docker as docker
import ost_utils.selenium.grid.podman as podman


def _has_podman():
    return os.system("podman --version &> /dev/null") == 0


def _has_podman_remote():
    return os.system("podman-remote --version &> /dev/null") == 0


def _has_docker():
    return os.system("docker -v &> /dev/null") == 0


def _grid_backend():
    env_backend = os.environ.get("OST_CONTAINER_BACKEND", None)
    if env_backend in ("docker", "podman", "podman-remote"):
        return env_backend

    if os_utils.inside_mock() and _has_podman_remote():
        return "podman-remote"

    if _has_podman():
        return "podman"

    if _has_docker():
        return "docker"


def _env_hub_url():
    return os.environ.get("OST_SELENIUM_HUB_URL", None)


@pytest.fixture(scope="session")
def hub_url(engine_fqdn, engine_ip, selenium_artifacts_dir):
    env_url = _env_hub_url()

    if env_url is not None:
        yield env_url
    else:
        backend = _grid_backend()
        if backend == "podman" or backend == "podman-remote":
            ui_artifacts_dir = selenium_artifacts_dir
            with podman.grid(
                engine_fqdn,
                engine_ip,
                podman_cmd=backend,
                ui_artifacts_dir=ui_artifacts_dir,
            ) as hub_url:
                yield hub_url
        elif backend == "docker":
            with docker.grid(engine_fqdn, engine_ip) as hub_url:
                yield hub_url
        else:
            raise RuntimeError(
                "No container backend available to set up the grid"
            )
