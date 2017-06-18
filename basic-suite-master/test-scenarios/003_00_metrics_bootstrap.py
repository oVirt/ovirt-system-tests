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

import nose.tools as nt
import os

try:
    import ovirtsdk4 as sdk4
    API_V3_ONLY = os.getenv('API_V3_ONLY', False)
    if API_V3_ONLY:
        API_V4 = False
    else:
        API_V4 = True
except ImportError:
    API_V4 = False

from ovirtlago import testlib


@testlib.with_ovirt_prefix
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
          '/usr/share/ovirt-engine-metrics/setup/ansible/'
          'configure_ovirt_machines_for_metrics.sh',
        ],
    )
    nt.eq_(
        result.code, 0, 'Configuring ovirt machines for metrics failed.'
                        ' Exit code is %s' % result.code
    )

    # Configure the engine-vm as the fluentd aggregator
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


_TEST_LIST = [
    #Disabling due to fluentd issues that needs to be debugged [18/06/17]
    #configure_metrics,
]


def test_gen():
    for t in testlib.test_sequence_gen(_TEST_LIST):
        test_gen.__name__ = t.description
        yield t
