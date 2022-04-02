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


@pytest.fixture(scope="session")
def artifact_list():
    return [
        '/etc/dnf',
        '/etc/firewalld',
        '/etc/httpd/conf',
        '/etc/httpd/conf.d',
        '/etc/httpd/conf.modules.d',
        '/etc/ovirt-engine',
        '/etc/ovirt-engine-dwh',
        '/etc/ovirt-engine-metrics',
        '/etc/ovirt-engine-setup.conf.d',
        '/etc/ovirt-engine-setup.env.d',
        '/etc/ovirt-host-deploy.conf.d',
        '/etc/ovirt-imageio-proxy',
        '/etc/ovirt-provider-ovn',
        '/etc/ovirt-vmconsole',
        '/etc/ovirt-web-ui',
        '/etc/resolv.conf',
        '/etc/sysconfig',
        '/etc/yum',
        '/etc/yum.repos.d',
        '/root',
        '/tmp/dnf_yum.conf',
        '/var/cache/ovirt-engine',
        '/var/lib/ovirt-engine/setup/answers',
        '/var/lib/ovirt-engine/ansible-runner',
        '/var/lib/pgsql/initdb_postgresql.log',
        '/var/lib/pgsql/data/log',
        '/var/log',
    ]


@pytest.fixture(scope="session")
def artifacts(all_hostnames, artifact_list):
    return {hostname: artifact_list for hostname in all_hostnames}


@pytest.fixture(scope="session", autouse=True)
def collect_artifacts(artifacts_dir, artifacts, ansible_by_hostname):
    def collect(hostname, artifacts_list, target_dir):
        artifacts_list_string = ','.join(artifacts_list)
        ansible_handle = ansible_by_hostname(hostname)
        archive_name = "artifacts.tar.gz"
        local_archive_dir = os.path.join(target_dir, "test_logs", hostname)
        local_archive_path = os.path.join(local_archive_dir, archive_name)
        remote_archive_path = os.path.join("/var/tmp", archive_name)
        os.makedirs(local_archive_dir, exist_ok=True)
        # Get the journal right before collecting, so that we get all
        # records we can. Does not make that much sense here, but doing
        # this in its own fixture, including making the effort to schedule
        # it right before current, would needlessly complicate the code.
        ansible_handle.shell('journalctl -a --no-pager -o short-iso-precise > ' '/var/log/journalctl.log')
        ansible_handle.archive(path=artifacts_list_string, dest=remote_archive_path)
        ansible_handle.fetch(src=remote_archive_path, dest=local_archive_path, flat='yes')
        shell.shell(["tar", "-xf", local_archive_path, "-C", local_archive_dir])
        shell.shell(["rm", local_archive_path])

    yield
    calls = [
        functools.partial(collect, hostname, artifact_list, artifacts_dir)
        for hostname, artifact_list in artifacts.items()
    ]
    utils.invoke_different_funcs_in_parallel(*calls)


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
def collect_vdsm_coverage_artifacts(artifacts_dir, ansible_host0, ansible_hosts):
    yield
    if os.environ.get("coverage", "false") == "true":
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
