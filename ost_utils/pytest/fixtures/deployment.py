#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import datetime
import functools
import getpass
import ipaddress
import logging
import os
import pprint

import pytest

from ost_utils import coverage
from ost_utils import deployment_utils
from ost_utils import utils
from ost_utils.deployment_utils import package_mgmt


LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def run_scripts(ansible_by_hostname, root_dir):
    def do_run_scripts(hostname, scripts):
        ansible_handle = ansible_by_hostname(hostname)
        for script in scripts:
            start = datetime.datetime.now()
            LOGGER.info(f"[{hostname}] Starting {script}")
            res = ansible_handle.script(os.path.join(root_dir, script))
            duration = int((datetime.datetime.now() - start).total_seconds())
            LOGGER.info(f"[{hostname}] Finished {script} ({duration}s)")
            LOGGER.debug(
                f"[{hostname}] Finished {script}, result:\n%s",
                pprint.pformat(res),
            )

    return do_run_scripts


@pytest.fixture(scope="session")
def set_sar_interval(ansible_all, root_dir):
    def do_set_sar_interval():
        ansible_all.file(
            path='/etc/systemd/system/sysstat-collect.timer.d',
            state='directory',
        )
        sar_stat_src_dir = os.path.join(root_dir, 'common/sar_stat')
        ansible_all.copy(
            src=os.path.join(sar_stat_src_dir, 'override.conf'),
            dest='/etc/systemd/system/sysstat-collect.timer.d',
        )
        ansible_all.systemd(
            daemon_reload='yes',
            name='sysstat-collect.timer',
            state='started',
            enabled='yes',
        )

    return do_set_sar_interval


def start_sshd_proxy(vms, host, root_dir, ssh_key_file):
    vms.copy(
        src=ssh_key_file,
        dest='/root/.ssh/id_rsa',
        mode='0600',
    )
    vms.copy(
        src=os.path.join(root_dir, 'common/helpers/sshd_proxy.service'),
        dest='/etc/systemd/system/sshd_proxy.service',
    )
    user = getpass.getuser()
    vms.copy(
        dest='/usr/local/sbin/sshd_proxy.sh',
        content=f'"#!/bin/bash\\nssh -D 1234 -p2222 -N -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i /root/.ssh/id_rsa {user}@{host}"',
        mode='0655',
    )
    vms.systemd(
        daemon_reload='yes',
        name='sshd_proxy.service',
        state='started',
        enabled='yes',
    )
    vms.lineinfile(
        path='/etc/dnf/dnf.conf',
        line='"proxy=socks5://localhost:1234\\nip_resolve=4"',
    )


@pytest.fixture(scope="session", autouse=True)
def deploy(
    ansible_vms_to_deploy,
    ansible_hosts,
    deploy_scripts,
    root_dir,
    working_dir,
    request,
    run_scripts,
    set_sar_interval,
    ost_images_distro,
    ssh_key_file,
    backend,
    management_network_name,
    management_network_supports_ipv4,
):
    if deployment_utils.is_deployed(working_dir):
        LOGGER.info("Environment already deployed")
        return

    LOGGER.info("Waiting for SSH on the VMs")
    ansible_vms_to_deploy.wait_for_connection(timeout=120)

    # set static hostname to match the one assigned by DNS
    ansible_vms_to_deploy.shell("hostnamectl set-hostname $(hostname)")

    # start IPv6 proxy for dnf so we can update packages
    if not management_network_supports_ipv4:
        LOGGER.info("Start sshd_proxy service and configure DNF for IPv6")
        # can't use a fixture since VMs may not be up yet
        ip = list(backend.ip_mapping().values())[0][management_network_name][0]
        start_sshd_proxy(
            ansible_vms_to_deploy,
            ipaddress.ip_interface(f"{ip}/64").network[1],
            root_dir,
            ssh_key_file,
        )

    # disable all repos
    # package_mgmt.disable_all_repos(ansible_vms_to_deploy)

    # add custom repos
    custom_repos = request.config.getoption('--custom-repo')
    if custom_repos is not None:
        repo_urls = package_mgmt.expand_repos(custom_repos, working_dir, ost_images_distro)
        package_mgmt.add_custom_repos(ansible_vms_to_deploy, repo_urls)
        ansible_vms_to_deploy.shell(
            'dnf upgrade --nogpgcheck -y --disableplugin versionlock -x ovirt-release-master,ovirt-release-master-tested,ovirt-engine-appliance,rhvm-appliance,ovirt-node-ng-image-update,redhat-virtualization-host-image-update'
        )
        # check if packages from custom repos were used
        if not request.config.getoption('--skip-custom-repos-check'):
            package_mgmt.check_installed_packages(ansible_vms_to_deploy)

    # report package versions
    package_mgmt.report_ovirt_packages_versions(ansible_vms_to_deploy)

    # run deployment scripts
    runs = [functools.partial(run_scripts, hostname, scripts) for hostname, scripts in deploy_scripts.items()]
    utils.invoke_different_funcs_in_parallel(*runs)

    # setup vdsm coverage on hosts if desired
    if os.environ.get("coverage", "false") == "true":
        coverage.vdsm.setup(ansible_hosts)

    # setup sar stat utility
    set_sar_interval()

    # mark env as deployed
    deployment_utils.mark_as_deployed(working_dir)
