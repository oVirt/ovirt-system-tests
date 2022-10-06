#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
from __future__ import absolute_import

import functools
import logging
import os

import pytest

from ost_utils import assert_utils
from ost_utils import utils
from ost_utils.ansible import AnsibleExecutionError

LOGGER = logging.getLogger(__name__)

LOG_COLLECTOR = """\
'[LogCollector]
user={engine_api_username}
passwd={engine_password}
engine={engine_fqdn}:443
local-tmp={local_tmp}
output=/dev/shm
'""".replace(
    '\n', '\\n'
)


@pytest.fixture
def setup_log_collector(ansible_engine, engine_password, engine_fqdn, engine_api_username):
    local_tmp = ansible_engine.tempfile(path='/dev/shm', state='directory')['path']
    ansible_engine.copy(
        dest='/root/ovirt-log-collector.conf',
        content=LOG_COLLECTOR.format(
            engine_api_username=engine_api_username,
            engine_password=engine_password,
            engine_fqdn=engine_fqdn,
            local_tmp=local_tmp,
        ),
    )


def configure_metrics(suite_dir, ansible_engine, ansible_hosts):
    """
    configure the setup for metrics collection. Essentially collectd and
    fluentd on each host and the engine. The engine will be also the central
    fluentd and will write to file, instead of ElasticSearch, and that will be
    an exported artifact of the suite.
    """

    # Use ovirt-engine-metrics to configure collectd + fluentd
    configyml = os.path.join(
        suite_dir,
        '../common/test-scenarios-files/metrics_bootstrap/config.yml',
    )
    ansible_engine.copy(src=configyml, dest='/etc/ovirt-engine-metrics/')

    ansible_engine.shell('/usr/share/ovirt-engine-metrics/configure_ovirt_machines_for_metrics.sh')

    # Configure the engine-vm as the fluentd aggregator
    if 'OST_FLUENTD_AGGREGATOR' in os.environ:
        metrics_bootstrap = os.path.join(suite_dir, '../common/test-scenarios-files/metrics_bootstrap')
        ansible_engine.copy(src=metrics_bootstrap, dest='/root/')

        ansible_engine.shell('ansible-playbook ' '/root/metrics_bootstrap/engine-fluentd-aggregator-playbook.yml')

    # clean /var/cache from yum leftovers. Frees up ~65M
    ansible_engine.file(path='/var/cache/dnf', state='absent')
    ansible_engine.file(path='/var/cache/yum', state='absent')
    ansible_hosts.file(path='/var/cache/dnf', state='absent')
    ansible_hosts.file(path='/var/cache/yum', state='absent')


def run_log_collector(ansible_engine):
    try:
        ansible_engine.shell(
            'ovirt-log-collector '
            '--verbose '
            '--batch '
            '--no-hypervisors '
            '--conf-file=/root/ovirt-log-collector.conf '
        )
    except AnsibleExecutionError as e:
        # log collector returns status code == 2 for warnings
        if e.rc != 2:
            raise

    ansible_engine.shell('rm -rf /dev/shm/sosreport-LogCollector-*')


def test_metrics_and_log_collector(setup_log_collector, suite_dir, ansible_engine, ansible_hosts):
    def configure():
        try:
            vt = utils.VectorThread(
                [
                    functools.partial(configure_metrics, suite_dir, ansible_engine, ansible_hosts),
                    functools.partial(run_log_collector, ansible_engine),
                ],
                daemon=True,
            )
            vt.start_all()
            vt.join_all(timeout=120)
        except utils.TimeoutException:
            LOGGER.debug("Metrics configuration timed out")
            return False
        return True

    assert assert_utils.true_within_short(configure)
