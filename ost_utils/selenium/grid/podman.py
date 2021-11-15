#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import contextlib
import json
import logging
import os
import time

import ost_utils.network_utils as network_utils

from ost_utils.selenium.grid import CHROME_CONTAINER_IMAGE
from ost_utils.selenium.grid import FIREFOX_CONTAINER_IMAGE
from ost_utils.selenium.grid import FFMPEG_CONTAINER_IMAGE
from ost_utils.selenium.grid import HUB_CONTAINER_IMAGE
from ost_utils.selenium.grid import SCREEN_WIDTH
from ost_utils.selenium.grid import SCREEN_HEIGHT
from ost_utils.shell import shell
from ost_utils.shell import ShellError


HUB_IP = "127.0.0.1"
HUB_PORT = 4444
NODE_PORT_GEN = iter(range(5600, 5700))
NODE_DISPLAY_ADDR_GEN = iter(range(100, 200))
GRID_STARTUP_WAIT_RETRIES = 300

LOGGER = logging.getLogger(__name__)


class SeleniumGridError(Exception):
    pass


@contextlib.contextmanager
def grid(
    engine_fqdn,
    engine_ip,
    node_images=[CHROME_CONTAINER_IMAGE, FIREFOX_CONTAINER_IMAGE],
    hub_image=HUB_CONTAINER_IMAGE,
    retries=3,
    podman_cmd="podman",
    ui_artifacts_dir=None,
):
    for attempt in range(retries):
        hub_port = network_utils.find_free_port(HUB_PORT, HUB_PORT + 100)

        LOGGER.debug(
            f"Attempt no {attempt} to run the grid on {hub_port} port"
        )

        try:
            with _grid(
                engine_fqdn,
                engine_ip,
                node_images,
                hub_image,
                hub_port,
                podman_cmd,
                ui_artifacts_dir,
            ) as url:
                LOGGER.debug(f"Grid is up: {url}")
                yield url
        except (SeleniumGridError, ShellError):
            if attempt < retries - 1:
                LOGGER.warning("Grid startup failed, retrying...")
            else:
                raise
        else:
            break


@contextlib.contextmanager
def _grid(
    engine_fqdn,
    engine_ip,
    node_images,
    hub_image,
    hub_port,
    podman_cmd,
    ui_artifacts_dir,
):

    with _pod(hub_port, podman_cmd) as pod_name:
        with _hub(
            hub_image, hub_port, pod_name, podman_cmd, ui_artifacts_dir
        ) as hub_name:
            engine_dns_entry = f"{engine_fqdn}:{engine_ip}"
            with _nodes(
                node_images,
                hub_name,
                pod_name,
                engine_dns_entry,
                podman_cmd,
                ui_artifacts_dir,
            ) as nodes_dict:
                node_names = [
                    node_dict['name'] for node_dict in nodes_dict.values()
                ]
                with _video_recorders(
                    pod_name, podman_cmd, nodes_dict, ui_artifacts_dir
                ) as videos_names:
                    url = f"http://{HUB_IP}:{hub_port}"
                    try:
                        grid_health_check(url, len(node_images))
                        yield url
                    except SeleniumGridError:
                        _log_issues(
                            pod_name,
                            hub_name,
                            node_names,
                            podman_cmd,
                            videos_names,
                        )
                        raise


@contextlib.contextmanager
def _pod(hub_port, podman_cmd):
    network_backend = os.getenv('PODMAN_NETWORK_BACKEND')
    if network_backend is None:
        network_backend_options = ["--network=slirp4netns:enable_ipv6=true"]
    else:
        network_backend_options = [
            f"--network={network_backend}:enable_ipv6=true"
        ]
    name = shell(
        [
            podman_cmd,
            "pod",
            "create",
            *network_backend_options,
            "-p",
            f'{hub_port}:4444',
        ]
    ).strip()
    try:
        yield name
    finally:
        shell([podman_cmd, "pod", "rm", "-f", name])


@contextlib.contextmanager
def _hub(image, hub_port, pod_name, podman_cmd, ui_artifacts_dir):
    hub_name = f"selenium-hub-{hub_port}"
    shell(
        [
            podman_cmd,
            "run",
            "-d",
            "--name",
            hub_name,
            "--pod",
            pod_name,
            image,
        ]
    ).strip()
    try:
        yield hub_name
    finally:
        save_container_logs(ui_artifacts_dir, hub_name, podman_cmd)
        shell([podman_cmd, "rm", "-f", hub_name])


# When running multiple containers in a pod, they compete over
# resources like network ports. This is why we can't simply run
# multiple selenium nodes in a single pod - we need to change
# the ports they're using by default and the 'DISPLAY' variable
# (we're using debug images which run VNC server) to some unique
# values.
@contextlib.contextmanager
def _nodes(
    images,
    hub_name,
    pod_name,
    engine_dns_entry,
    podman_cmd,
    ui_artifacts_dir,
):
    nodes_dict = {}

    for image in images:
        display = next(NODE_DISPLAY_ADDR_GEN)
        name = shell(
            [
                podman_cmd,
                "run",
                "-d",
                "-v",
                "/dev/shm:/dev/shm",
                "-v",
                f"{ui_artifacts_dir}:/export:Z",
                f"--add-host={engine_dns_entry}",
                "-e",
                f"SE_EVENT_BUS_HOST={hub_name}",
                "-e",
                "SE_EVENT_BUS_PUBLISH_PORT=4442",
                "-e",
                "SE_EVENT_BUS_SUBSCRIBE_PORT=4443",
                "-e",
                f"SE_OPTS=--port {next(NODE_PORT_GEN)}",
                "-e",
                f"DISPLAY_NUM={display}",
                "-e",
                f"DISPLAY=:{display}",
                "-e",
                f"VNC_PORT={next(NODE_PORT_GEN)}",
                "-e",
                "VNC_NO_PASSWORD=1",
                "-e",
                f"SCREEN_WIDTH={SCREEN_WIDTH}",
                "-e",
                f"SCREEN_HEIGHT={SCREEN_HEIGHT}",
                "--pod",
                pod_name,
                image,
            ]
        ).strip()
        nodes_dict.update({image: {'name': name, 'display': display}})

    try:
        yield nodes_dict
    finally:
        for node_dict in nodes_dict.values():
            save_container_logs(
                ui_artifacts_dir, node_dict['name'], podman_cmd, "worker_"
            )
            shell([podman_cmd, "rm", "-f", node_dict['name']])


@contextlib.contextmanager
def _video_recorders(pod_name, podman_cmd, nodes_dict, ui_artifacts_dir):
    videos = []
    if ui_artifacts_dir is not None:
        for image, values in nodes_dict.items():
            video = shell(
                [
                    podman_cmd,
                    "run",
                    "-d",
                    "-v",
                    f"{ui_artifacts_dir}:/videos:Z",
                    "-e",
                    f"DISPLAY_CONTAINER_NAME={' '}",
                    "-e",
                    f"DISPLAY={values['display']}",
                    "-e",
                    f"FILE_NAME=video-{image.split('/')[-1].split('-')[1]}"
                    f".mp4",
                    "-e",
                    f"VIDEO_SIZE={SCREEN_WIDTH}x{SCREEN_HEIGHT}",
                    "--pod",
                    pod_name,
                    FFMPEG_CONTAINER_IMAGE,
                ]
            ).strip()
            videos.append(video)

    try:
        yield videos
    finally:
        for video in videos:
            shell([podman_cmd, "stop", video])
            save_container_logs(ui_artifacts_dir, video, podman_cmd, "video_")
            shell([podman_cmd, "rm", "-f", video])


def grid_health_check(hub_url, expected_node_count=None):
    status_url = hub_url + "/status"

    for i in range(GRID_STARTUP_WAIT_RETRIES):
        try:
            status_json = shell(["curl", "-sSL", status_url])
            status_dict = json.loads(status_json)
            if (
                status_dict["value"]["ready"] is True
                and len(status_dict["value"]["nodes"]) == expected_node_count
                and _all_nodes_up(status_dict["value"]["nodes"])
            ):
                break
        except ShellError:
            pass
        time.sleep(0.1)
    else:
        raise SeleniumGridError("Selenium grid didn't start up properly")


def _all_nodes_up(nodes_dict):
    for node in nodes_dict:
        if node["availability"] != "UP":
            return False
    return True


def _log_issues(pod_name, hub_name, node_names, podman_cmd, videos_names):
    LOGGER.error(
        "Pod inspection: \n%s"
        % shell([podman_cmd, "pod", "inspect", pod_name])
    )
    LOGGER.error("Hub logs: \n%s" % shell([podman_cmd, "logs", hub_name]))
    for name in node_names:
        LOGGER.error(
            "Node %s logs: \n%s" % (name, shell([podman_cmd, "logs", name]))
        )
    for video in videos_names:
        LOGGER.error(
            "Video %s logs: \n%s" % (video, shell([podman_cmd, "logs", video]))
        )


def save_container_logs(
    ui_artifacts_dir, container_name, podman_cmd, name_prefix=""
):
    log_dir_path = os.path.join(ui_artifacts_dir, 'selenium_grid_nodes')
    os.makedirs(log_dir_path, exist_ok=True)
    file_path = os.path.join(
        log_dir_path, name_prefix + container_name + '.log'
    )
    with open(file_path, "w", encoding='UTF8') as log_file:
        log_file.write(shell([podman_cmd, "logs", container_name]))
