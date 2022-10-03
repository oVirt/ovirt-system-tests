#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import json
import logging
import os
import time

from datetime import datetime

import pytest

import ovirtsdk4.types as types

from ost_utils import network_utils
from ost_utils.selenium.grid import browser
from ost_utils.shell import ShellError
from ost_utils.shell import shell

GRID_STARTUP_WAIT_RETRIES = 300


class SeleniumGridError(Exception):
    pass


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _node_ready(status_dict, browser_name):
    nodes = status_dict["value"]["nodes"]
    for node in nodes:
        for slot in node["slots"]:
            if slot["stereotype"]["browserName"] == browser_name and node["availability"] == "UP":
                return True
    return False


def _grid_health_check(hub_url, browser_name):
    status_url = hub_url + "/status"

    for i in range(GRID_STARTUP_WAIT_RETRIES):
        try:
            status_json = shell(["curl", "-sSL", status_url])
            status_dict = json.loads(status_json)
            if status_dict["value"]["ready"] and _node_ready(status_dict, browser_name):
                return True
        except ShellError:
            pass
        time.sleep(0.1)

    raise SeleniumGridError("Selenium grid didn't start up properly")


@pytest.fixture(
    scope="session",
    params=[
        pytest.param(browser.chrome_options(), id="chrome"),
        pytest.param(browser.firefox_options(), id="firefox"),
    ],
)
def selenium_browser_options(request):
    return request.param


@pytest.fixture(scope="session")
def selenium_browser_name(selenium_browser_options):
    return selenium_browser_options.to_capabilities()['browserName']


@pytest.fixture(scope="session")
def selenium_browser_image(selenium_browser_name):
    # synchronize changes with https://github.com/oVirt/ost-images/blob/master/configs/storage/setup_selenium_grid.sh
    return f"quay.io/ovirt/selenium-standalone-{selenium_browser_name}:4.4.0"


@pytest.fixture(scope="session")
def selenium_port():
    return 4444


@pytest.fixture(scope="session")
def selenium_screen_width():
    return 1600


@pytest.fixture(scope="session")
def selenium_screen_height():
    return 900


@pytest.fixture(scope="session")
def selenium_remote_artifacts_dir():
    return "/var/tmp/selenium"


@pytest.fixture(scope="session")
def selenium_url(storage_management_ips, selenium_port):
    ip = network_utils.ip_to_url(storage_management_ips[0])
    url = f"http://{ip}:{selenium_port}"
    yield url


@pytest.fixture(scope="module")
def selenium_browser(
    ansible_storage,
    selenium_artifacts_dir,
    selenium_browser_image,
    selenium_browser_name,
    selenium_port,
    selenium_remote_artifacts_dir,
    selenium_url,
    selenium_screen_height,
    selenium_screen_width,
):
    container_id = ansible_storage.shell(
        "podman run -d"
        f" -p {selenium_port}:{selenium_port}"
        "  -p 7900:7900"
        "  --network=slirp4netns:enable_ipv6=true"
        "  --shm-size=1500m"
        f" -v {selenium_remote_artifacts_dir}/:/export:z"
        f" -e SCREEN_WIDTH={selenium_screen_width}"
        f" -e SCREEN_HEIGHT={selenium_screen_height}"
        "  -e SE_OPTS='--log-level FINE'"
        "  -e SE_VNC_NO_PASSWORD=1"
        f" {selenium_browser_image}"
    )["stdout"].strip()
    _grid_health_check(selenium_url, selenium_browser_name)
    yield container_id
    ansible_storage.shell(f"podman stop {container_id}")
    log_name = f"podman-{selenium_browser_name}-{_timestamp()}.log"
    remote_log_path = f"{selenium_remote_artifacts_dir}/{log_name}"
    ansible_storage.shell(f"podman logs {container_id} > {remote_log_path}")
    ansible_storage.fetch(src=remote_log_path, dest=f"{selenium_artifacts_dir}/{log_name}", flat=True)


@pytest.fixture(scope="module")
def selenium_video_recorder(
    ansible_storage,
    selenium_browser_name,
    selenium_browser,
    selenium_artifacts_dir,
    selenium_remote_artifacts_dir,
    selenium_screen_width,
    selenium_screen_height,
):
    video_file_name = f"video-{selenium_browser_name}-{_timestamp()}.mp4"
    container_id = ansible_storage.shell(
        "podman run -d"
        f" -v {selenium_remote_artifacts_dir}/:/videos:z"
        f" -e DISPLAY_CONTAINER_NAME={selenium_browser[:12]}"
        f" -e FILE_NAME={video_file_name}"
        f" -e SE_SCREEN_WIDTH={selenium_screen_width}"
        f" -e SE_SCREEN_HEIGHT={selenium_screen_height}"
        f" --network=container:{selenium_browser}"
        "  quay.io/ovirt/selenium-video:latest"
    )["stdout"].strip()
    yield
    ansible_storage.shell(f"podman stop {container_id}")
    ansible_storage.fetch(
        src=f"{selenium_remote_artifacts_dir}/{video_file_name}",
        dest=selenium_artifacts_dir,
        flat=True,
    )
    res = ansible_storage.shell(f"podman logs {container_id}")

    with open(f"{selenium_artifacts_dir}/podman-video-{selenium_browser}-{_timestamp()}.log", "w") as log_file:
        log_file.write(res["stdout"])


@pytest.fixture(scope="module")
def selenium_grid_url(selenium_url, selenium_browser, selenium_video_recorder):
    yield selenium_url


@pytest.fixture(scope="module", autouse=True)
def selenium_disable_noisy_logging():
    selenium_logger = logging.getLogger('selenium')
    selenium_logger_level = selenium_logger.getEffectiveLevel()
    selenium_logger.setLevel(logging.WARNING)

    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger_level = urllib3_logger.getEffectiveLevel()
    urllib3_logger.setLevel(logging.WARNING)

    yield

    selenium_logger.setLevel(selenium_logger_level)
    urllib3_logger.setLevel(urllib3_logger_level)


@pytest.fixture(scope="module", autouse=True)
def selenium_disable_notifications_for_admin_user(engine_admin_service):
    targetName = "webAdmin.showNotifications"
    existingProps = [option for option in engine_admin_service.options_service().list() if option.name == targetName]
    if not existingProps:
        option = types.UserOption(name=targetName, content="false", user=engine_admin_service.get())
        assert engine_admin_service.options_service().add(option, wait=True)


@pytest.fixture(scope="session")
def selenium_artifacts_dir(artifacts_dir):
    dc_version = os.environ.get('OST_DC_VERSION', '')
    path = os.path.join(artifacts_dir, 'ui_tests_artifacts%s/' % dc_version)
    os.umask(0)
    os.makedirs(path, mode=0o777, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def selenium_artifact_filename(selenium_browser_name):
    def _selenium_artifact_filename(description, extension):
        return f"{_timestamp()}_{selenium_browser_name}_{description}.{extension}"

    return _selenium_artifact_filename


@pytest.fixture(scope="session")
def selenium_artifact_full_path(selenium_artifacts_dir, selenium_artifact_filename):
    def _selenium_artifact_full_path(description, extension):
        return os.path.join(
            selenium_artifacts_dir,
            selenium_artifact_filename(description, extension),
        )

    return _selenium_artifact_full_path
