#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import functools
import logging
import os

import pytest

from ost_utils import coverage
from ost_utils import utils
from ost_utils import shell
from ost_utils.ansible import AnsibleExecutionError

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def artifacts_dir():
    return os.path.join(os.environ["OST_REPO_ROOT"], "exported-artifacts")


@pytest.fixture(scope="session", autouse=True)
def collect_artifacts(root_dir):
    yield
    ost_script = os.path.join(root_dir, "ost.sh")
    shell.shell(f"{ost_script} fetch-artifacts", shell=True)


@pytest.fixture(scope="session", autouse=True)
def generate_sar_stat_plots(collect_artifacts, ansible_all, ansible_by_hostname, artifacts_dir):
    def generate(hostname):
        ansible_handle = ansible_by_hostname(hostname)
        try:
            # DEV and EDEV statistics are excluded, since they contain
            # the iface names - semicolons in ';vdsmdummy;' iface name cause
            # sadf to fail.
            # TODO: change the name of the iface in question
            ansible_handle.shell(
                'sadf -g -- -bBdFHqSuvwWy -I SUM -I ALL -m ALL -n NFS,NFSD,'
                'SOCK,IP,EIP,ICMP,EICMP,TCP,ETCP,UDP,SOCK6,IP6,EIP6,ICMP6,'
                'EICMP6,UDP6 -r ALL -u ALL -P ALL > /var/tmp/sarstat.svg'
            )
        except AnsibleExecutionError as err:
            # sar error should not fail the run
            LOGGER.error(f"Failed generating sar report on '{hostname}': {err}")
        else:
            ansible_handle.fetch(
                src='/var/tmp/sarstat.svg',
                dest=f'{artifacts_dir}/{hostname}.sarstat.svg',
                flat=True,
            )

    yield
    calls = [functools.partial(generate, res['stdout']) for res in ansible_all.shell("hostname").values()]
    utils.invoke_different_funcs_in_parallel(*calls)


@pytest.fixture(scope="session", autouse=True)
def collect_vdsm_coverage_artifacts(artifacts_dir, ansible_host0, ansible_hosts, request):
    yield
    if request.config.getoption('--vdsm-coverage'):
        output_path = os.path.join(artifacts_dir, "coverage/")
        os.makedirs(output_path, exist_ok=True)
        coverage.vdsm.collect(ansible_host0, ansible_hosts, output_path)


@pytest.fixture(scope="session", autouse=True)
def dump_dhcp_leases(artifacts_dir, backend, management_network_name):
    yield
    shell.shell(
        [
            'bash',
            '-c',
            f'virsh net-dhcp-leases {backend.libvirt_net_name(management_network_name)} > {artifacts_dir}/libvirt-leases',
        ]
    )
