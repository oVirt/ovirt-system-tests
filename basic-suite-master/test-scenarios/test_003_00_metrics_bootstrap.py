#
# Copyright 2014 Red Hat, Inc.
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
from __future__ import absolute_import

import functools
import os

from ost_utils import utils
from ost_utils.ansible import AnsibleExecutionError


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
        '../common/test-scenarios-files/metrics_bootstrap/config.yml'
    )
    ansible_engine.copy(src=configyml, dest='/etc/ovirt-engine-metrics/')

    ansible_engine.shell(
      '/usr/share/ovirt-engine-metrics/configure_ovirt_machines_for_metrics.sh'
    )

    # Configure the engine-vm as the fluentd aggregator
    if 'OST_FLUENTD_AGGREGATOR' in os.environ:
        metrics_bootstrap = os.path.join(
            suite_dir,
            '../common/test-scenarios-files/metrics_bootstrap'
        )
        ansible_engine.copy(src=metrics_bootstrap, dest='/root/')

        ansible_engine.shell(
            'ansible-playbook '
            '/root/metrics_bootstrap/engine-fluentd-aggregator-playbook.yml'
        )

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


def test_metrics_and_log_collector(suite_dir, ansible_engine, ansible_hosts):
    vt = utils.VectorThread(
        [
            functools.partial(configure_metrics, suite_dir, ansible_engine,
                              ansible_hosts),
            functools.partial(run_log_collector, ansible_engine),
        ],
    )
    vt.start_all()
    vt.join_all()
