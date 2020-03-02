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
import nose.tools as nt
import os

from lago import utils
from ovirtlago import testlib

import test_utils


@testlib.with_ovirt_prefix
def configure_vdsm_sos_plugin(prefix):
    """
     VDSM SOS plugin has been moved from VDSM to SOS as a part of:
        sos-3.7-3 in CentOS/RHEL 7.7
        sos-3.7.1 in Fedora
     In the transition period we need to ensure that VDSM SOS plugin exists
     on hosts for metrics to configure properly, so we will need to copy it
     manually to hosts if not exists (ie installed by sos package)
    """
    plugin_setup = os.path.join(
        os.environ.get('SUITE'),
        '../common/test-scenarios-files/vdsm-sos-plugin'
    )
    hosts = prefix.virt_env.host_vms()
    for host in hosts:
        host.copy_to(
            plugin_setup,
            '/tmp'
        )
        host.ssh(['/tmp/vdsm-sos-plugin/install-plugin.sh'])


def configure_metrics(prefix):
    """
     configure the setup for metrics collection. Essentially collectd and
     fluentd on each host and the engine. The engine will be also the central
     fluentd and will write to file, instead of ElasticSearch, and that will be
     an exported artifact of the suite.
    """

    engine = prefix.virt_env.engine_vm()

    # Use ovirt-engine-metrics to configure collectd + fluentd
    configyml = os.path.join(
        os.environ.get('SUITE'),
        '../common/test-scenarios-files/metrics_bootstrap/config.yml'
    )
    engine.copy_to(configyml, '/etc/ovirt-engine-metrics/')

    result = engine.ssh(
        [
          '/usr/share/ovirt-engine-metrics/'
          'configure_ovirt_machines_for_metrics.sh',
        ],
    )
    nt.eq_(
        result.code, 0, 'Configuring ovirt machines for metrics failed.'
                        ' Exit code is %s' % result.code
    )

    # Configure the engine-vm as the fluentd aggregator
    if 'OST_FLUENTD_AGGREGATOR' in os.environ:
        metrics_bootstrap = os.path.join(
            os.environ.get('SUITE'),
            '../common/test-scenarios-files/metrics_bootstrap'
        )
        engine.copy_to(metrics_bootstrap, '/root')

        result = engine.ssh(
            [
                'ansible-playbook',
                '/root/metrics_bootstrap/engine-fluentd-aggregator-playbook.yml',
            ],
        )
        nt.eq_(
            result.code, 0, 'Configuring ovirt-engine as fluentd aggregator failed.'
                            ' Exit code is %s' % result.code
        )

    # clean /dev/shm from yum leftovers. Frees up ~65M
    engine.ssh(['rm', '-rf', '/dev/shm/yum*', '/dev/shm/*.rpm'])
    hosts = prefix.virt_env.host_vms()
    for host in hosts:
        host.ssh(['rm', '-rf', '/dev/shm/yum*', '/dev/shm/*.rpm'])


def run_log_collector(prefix):
    engine = prefix.virt_env.engine_vm()
    result = engine.ssh(
        [
            'ovirt-log-collector',
            '--verbose',
            '--batch',
            '--no-hypervisors',
            '--conf-file=/root/ovirt-log-collector.conf',
        ],
    )
    # log collector returns status code == 2 for warnings
    nt.assert_true(
        result.code in (0, 2),
        'log collector failed. Exit code is %s' % result.code
    )

    engine.ssh(
        [
            'rm',
            '-rf',
            '/dev/shm/sosreport-LogCollector-*',
        ],
    )


@testlib.with_ovirt_prefix
def metrics_and_log_collector(prefix):
    vt = utils.VectorThread(
            [
                functools.partial(configure_metrics, prefix),
                functools.partial(run_log_collector, prefix),
            ],
        )
    vt.start_all()
    vt.join_all()


_TEST_LIST = [
    configure_vdsm_sos_plugin,
    metrics_and_log_collector,
]


def test_gen():
    for t in test_utils.test_gen(_TEST_LIST, test_gen):
        test_utils.test_invocation_logger(__name__ + '#' + t.description)
        yield t
