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

from lago import sdk


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
    for host in hosts:
        host.ssh(['systemctl', 'stop', 'vdsmd', 'supervdsmd'])


def _collect_coverage_data_file_names(host):
    # print coverage data files as basenames to reduce output size - someone
    # (paramiko?) trims ssh's commands outputs when they're very long
    cmd = ('"ls /var/lib/vdsm/coverage/vdsm.coverage.* |'
           ' tr \'\\n\' \'\\0\' | xargs -0 -n 1 basename"')
    args = ['/bin/bash', '-c', cmd]
    command_status = host.ssh(args)
    return command_status.out.split()


def _copy_coverage_data_to_first_host(first_host, remaining_hosts):
    # coverage.py needs source files at the moment of report generation -
    # that's why we need to do it on one of the hosts
    try:
        tmpdir = tempfile.mkdtemp()
        for host in remaining_hosts:
            coverage_data_files = _collect_coverage_data_file_names(host)
            for coverage_data_file in coverage_data_files:
                coverage_data_file = os.path.join('/var/lib/vdsm/coverage',
                                                  coverage_data_file)
                host.copy_from(coverage_data_file, tmpdir)
        for coverage_data_file in os.listdir(tmpdir):
            coverage_data_file = os.path.join(tmpdir, coverage_data_file)
            first_host.copy_to(coverage_data_file, '/var/lib/vdsm/coverage')
    finally:
        shutil.rmtree(tmpdir)


def _generate_coverage_report_on_host(host):
    host.ssh(['coverage', 'combine',
              '--rcfile=/var/lib/vdsm/coverage/coveragerc'])
    host.ssh(['coverage', 'html',
              '--directory=/var/lib/vdsm/coverage/html',
              '--rcfile=/var/lib/vdsm/coverage/coveragerc'])


def _copy_coverage_report_from_host(host, output_path):
    host.copy_from('/var/lib/vdsm/coverage/coveragerc', output_path)
    host.copy_from('/var/lib/vdsm/coverage/vdsm.coverage', output_path)
    host.copy_from('/var/lib/vdsm/coverage/html', output_path)


def generate_coverage_report(prefix_path, output_path):
    prefix = sdk.load_env(prefix_path)
    hosts = [h for h in six.itervalues(prefix.get_vms())
             if h.vm_type == 'ovirt-host']
    _stop_vdsm_services(hosts)
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
