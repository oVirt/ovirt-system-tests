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

from ost_utils import assert_utils
from ost_utils import coverage
from ost_utils import deployment_utils
from ost_utils import utils
from ost_utils.ansible import AnsibleExecutionError
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
    ansible_all,
    ansible_hosts,
    deploy_scripts,
    deploy_hosted_engine,
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

    def all_vms_up():
        result = ansible_all.shell("systemctl is-active default.target")
        return all(v["stdout"] == "active" for v in result.values())

    LOGGER.info("Waiting for VMs to fully boot")
    assert assert_utils.true_within_short(all_vms_up, allowed_exceptions=[AnsibleExecutionError])

    # set static hostname to match the one assigned by DNS
    ansible_all.shell("hostnamectl set-hostname $(hostname)")

    # start IPv6 proxy for dnf so we can update packages
    if not management_network_supports_ipv4:
        LOGGER.info("Start sshd_proxy service and configure DNF for IPv6")
        # can't use a fixture since VMs may not be up yet
        ip = list(backend.ip_mapping().values())[0][management_network_name][0]
        start_sshd_proxy(
            ansible_all,
            ipaddress.ip_interface(f"{ip}/64").network[1],
            root_dir,
            ssh_key_file,
        )

    # disable all repos
    package_mgmt.disable_all_repos(ansible_all)

    # add custom repos
    custom_repos = request.config.getoption('--custom-repo')
    if custom_repos is not None:
        repo_urls = package_mgmt.expand_repos(custom_repos, working_dir, ost_images_distro)
        package_mgmt.add_custom_repos(ansible_all, repo_urls)
        ansible_all.shell(
            'dnf upgrade --nogpgcheck -y --disableplugin versionlock -x ovirt-release-master,ovirt-release-master-tested,ovirt-engine-appliance,rhvm-appliance,ovirt-node-ng-image-update,redhat-virtualization-host-image-update,ovirt-release-host-node'
        )
        # check if packages from custom repos were used
        if not request.config.getoption('--skip-custom-repos-check') and not deploy_hosted_engine:
            package_mgmt.check_installed_packages(ansible_all)

    # temporary hack to downgrade python on host-0 to investigate https://bugzilla.redhat.com/show_bug.cgi?id=2111187
    if ost_images_distro == "el8stream":
        ansible_hosts.shell(
            '(hostname | grep 0) && dnf install -y --enablerepo baseos platform-python-3.6.8-42.el8 || :'
        )

    # report package versions
    package_mgmt.report_ovirt_packages_versions(ansible_all)

    # run deployment scripts
    runs = [functools.partial(run_scripts, hostname, scripts) for hostname, scripts in deploy_scripts.items()]
    utils.invoke_different_funcs_in_parallel(*runs)

    # setup vdsm coverage on hosts if desired
    if request.config.getoption('--vdsm-coverage'):
        coverage.vdsm.setup(ansible_hosts)

    # setup sar stat utility
    set_sar_interval()

    # mark env as deployed
    deployment_utils.mark_as_deployed(working_dir)
