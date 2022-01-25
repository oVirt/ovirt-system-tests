#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import contextlib
import logging
import os
import tarfile
import tempfile

VDSM_CONF_DIR = '/etc/vdsm/vdsm.conf.d'
VDSM_COVERAGE_CONF_PATH = f'{VDSM_CONF_DIR}/coverage.conf'
VDSM_COVERAGE_CONF = "'[devel]\\ncoverage_enable = true'"

COVERAGE_DIR = '/var/lib/vdsm/coverage'
COVERAGE_DATA = f'{COVERAGE_DIR}/vdsm.coverage'
COVERAGE_HTML = f'{COVERAGE_DIR}/html'
COVERAGE_RC = f'{COVERAGE_DIR}/coveragerc'
COVERAGE_CONF = f"""\
'[run]
branch = True
concurrency = thread multiprocessing
parallel = True
data_file = {COVERAGE_DATA}
source = vdsm, yajsonrpc'
""".replace(
    '\n', '\\n'
)


def setup(ansible_hosts):
    logging.debug('Setting up VDSM coverage...')

    # ulgy workaround for FIPS...
    ansible_hosts.replace(
        path='/usr/lib64/python3.6/site-packages/coverage/misc.py',
        regexp='md5',
        replace='sha1',
    )

    ansible_hosts.copy(dest=VDSM_COVERAGE_CONF_PATH, content=VDSM_COVERAGE_CONF)

    ansible_hosts.file(path=COVERAGE_DIR, state='directory', mode='0777')
    ansible_hosts.copy(dest=COVERAGE_RC, content=COVERAGE_CONF)

    added_line = f'COVERAGE_PROCESS_START="{COVERAGE_RC}"'
    ansible_hosts.lineinfile(path='/etc/sysconfig/vdsm', line=added_line, create=True)
    ansible_hosts.lineinfile(path='/etc/sysconfig/supervdsmd', line=added_line, create=True)


def collect(ansible_host0, ansible_hosts, output_path):
    logging.debug('Collecting VDSM coverage report...')
    with _stop_vdsm_services(ansible_hosts):
        _combine_coverage_data_on_hosts(ansible_hosts)
        _copy_coverage_data_to_first_host(ansible_host0, ansible_hosts)
        _generate_coverage_report_on_host(ansible_host0)
        _copy_coverage_report_from_host(ansible_host0, output_path)


@contextlib.contextmanager
def _stop_vdsm_services(hosts):
    """
    need to stop gracefully both vdsmd and supervdsmd to make
    coverage.py dump coverage data
    """
    try:
        logging.debug('Stopping VDSM services...')
        hosts.systemd(name='vdsmd', state='stopped')
        hosts.systemd(name='supervdsmd', state='stopped')
        yield
    finally:
        logging.debug('Restarting VDSM services...')
        hosts.systemd(name='vdsmd', state='started')
        hosts.systemd(name='supervdsmd', state='started')


def _combine_coverage_data_on_hosts(hosts):
    logging.debug('Combining coverage data on hosts...')
    hosts.shell(f'coverage-3 combine --rcfile={COVERAGE_RC}')


def _copy_coverage_data_to_first_host(host0, hosts):
    """
    coverage.py needs source files at the moment of report generation -
    that's why we need to do it on one of the hosts
    """
    logging.debug('Copying coverage data to one of the hosts...')
    with tempfile.TemporaryDirectory() as tmpdir:
        hosts.fetch(src=COVERAGE_DATA, dest=tmpdir)
        for host in os.listdir(tmpdir):
            src_path = os.path.join(tmpdir, host, COVERAGE_DATA[1:])
            dest_path = os.path.join(COVERAGE_DIR, f'vdsm.coverage.{host}')
            host0.copy(src=src_path, dest=dest_path)


def _generate_coverage_report_on_host(host):
    logging.debug('Generating coverage report on one of the hosts...')
    host.shell(f'coverage-3 combine -a --rcfile={COVERAGE_RC}')
    # Using the "--ignore-errors" flag because we generate the coverage report
    # on host-0 but do not have 'vdsm-gluster' installed there.
    host.shell(f'coverage-3 html --ignore-errors --directory={COVERAGE_HTML} --rcfile={COVERAGE_RC}')


def _copy_coverage_report_from_host(host, output_path):
    logging.debug('Copying generated coverage report from one of the hosts...')
    # fetch does not support recursion
    html_tar = f'{COVERAGE_HTML}.tar'
    host.shell(
        f'tar -cf {html_tar} {os.path.basename(COVERAGE_HTML)}',
        chdir=os.path.dirname(COVERAGE_HTML),
    )

    for file in [COVERAGE_RC, COVERAGE_DATA, html_tar]:
        host.fetch(src=file, dest=output_path, flat=True)

    local_tar = os.path.join(output_path, os.path.basename(html_tar))
    with tarfile.open(local_tar) as tar:
        tar.extractall(output_path)

    host.file(path=html_tar, state='absent')
    os.remove(local_tar)
