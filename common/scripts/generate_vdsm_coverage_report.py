#
# Copyright 2018 Red Hat, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from __future__ import absolute_import
from __future__ import print_function

import os
import os.path
import shutil
import sys
import tempfile

from textwrap import dedent

import six

from lago import sdk, utils


def usage():
    msg = \
        """
        Usage: generate_vdsm_coverage_report PREFIX_PATH OUTPUT_PATH

        Creates a VDSM coverage report on one of the hosts from
        data gathered from all the hosts.

        PREFIX_PATH path to a lago prefix.
        OUTPUT_PATH existing directory where coverage report will be copied
        """
    print(dedent(msg))


def _stop_vdsm_services(hosts):
    # need to stop gracefully both vdsmd and supervdsmd
    # to make coverage.py dump coverage data
    print("Stopping VDSM services...")

    def _stop_vdsm_services_on_host(host):
        host.ssh(['systemctl', 'stop', 'vdsmd', 'supervdsmd'])

    utils.invoke_in_parallel(_stop_vdsm_services_on_host, hosts)


def _combine_coverage_data_on_hosts(hosts):
    print("Combining coverage data on hosts...")

    def _combine_coverage_data_on_host(host):
        host.ssh(['$([ -x /usr/bin/coverage ] && echo coverage || echo coverage-3)', 'combine',
                  '--rcfile=/var/lib/vdsm/coverage/coveragerc'])

    utils.invoke_in_parallel(_combine_coverage_data_on_host, hosts)


def _copy_coverage_data_to_first_host(first_host, remaining_hosts):
    # coverage.py needs source files at the moment of report generation -
    # that's why we need to do it on one of the hosts
    print("Copying coverage data to one of the hosts...")
    try:
        tmpdir = tempfile.mkdtemp()

        def _copy_coverage_data_from_host(host_idx, host):
            target_coverage_file_name = 'vdsm.coverage.{}'.format(host_idx)
            host.copy_from('/var/lib/vdsm/coverage/vdsm.coverage',
                           os.path.join(tmpdir, target_coverage_file_name))

        utils.invoke_in_parallel(_copy_coverage_data_from_host,
                                 tuple(range(len(remaining_hosts))),
                                 remaining_hosts)

        for coverage_data_file in os.listdir(tmpdir):
            coverage_data_file = os.path.join(tmpdir, coverage_data_file)
            first_host.copy_to(coverage_data_file, '/var/lib/vdsm/coverage')
    finally:
        shutil.rmtree(tmpdir)


def _generate_coverage_report_on_host(host):
    print("Generating coverage report on one of the hosts...")
    host.ssh(['$([ -x /usr/bin/coverage ] && echo coverage || echo coverage-3)', 'combine', '-a',
              '--rcfile=/var/lib/vdsm/coverage/coveragerc'])
    host.ssh(['$([ -x /usr/bin/coverage ] && echo coverage || echo coverage-3)', 'html',
              '--directory=/var/lib/vdsm/coverage/html',
              '--rcfile=/var/lib/vdsm/coverage/coveragerc'])


def _copy_coverage_report_from_host(host, output_path):
    print("Copying generated coverage report from one of the hosts...")
    host.copy_from('/var/lib/vdsm/coverage/coveragerc', output_path)
    host.copy_from('/var/lib/vdsm/coverage/vdsm.coverage', output_path)
    host.copy_from('/var/lib/vdsm/coverage/html', output_path)


def generate_coverage_report(prefix_path, output_path):
    prefix = sdk.load_env(prefix_path)
    hosts = [h for h in six.itervalues(prefix.get_vms())
             if h.vm_type == 'ovirt-host']
    _stop_vdsm_services(hosts)
    _combine_coverage_data_on_hosts(hosts)
    _copy_coverage_data_to_first_host(hosts[0], hosts[1:])
    _generate_coverage_report_on_host(hosts[0])
    _copy_coverage_report_from_host(hosts[0], output_path)


def main():
    if len(sys.argv) != 3:
        usage()
        sys.exit(1)

    generate_coverage_report(prefix_path=sys.argv[1], output_path=sys.argv[2])


if __name__ == '__main__':
    main()
