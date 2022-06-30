#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging
import os

import pytest

from ost_utils import assert_utils
from ost_utils import he_utils
from ost_utils.deployment_utils import package_mgmt


def test_run_dig_loop(
    suite_dir,
    ansible_hosts,
):
    dig_loop_src_dir = os.path.join(suite_dir, 'dig_loop')
    ansible_hosts.copy(
        src=os.path.join(
            dig_loop_src_dir,
            'run_dig_loop.sh',
        ),
        dest='/usr/local/sbin',
        mode='preserve',
    )
    ansible_hosts.copy(
        src=os.path.join(
            dig_loop_src_dir,
            'rundigloop.service',
        ),
        dest='/etc/systemd/system',
    )
    ansible_hosts.systemd(
        daemon_reload='yes',
        name='rundigloop',
        state='started',
        enabled='yes',
    )


def test_lower_ha_agent_vdsm_connection_timeout(
    ansible_host0,
    ansible_all,
):
    conspath = ansible_host0.shell(
        "python3 -c " "'from ovirt_hosted_engine_ha.env import constants; " "print(constants.__file__)'"
    )['stdout_lines'][0]
    ansible_all.lineinfile(
        path=conspath,
        create=True,
        regexp='^VDSCLI_SSL_TIMEOUT',
        # Defaults to 900 seconds, too much for OST
        # Need to pass quoted, as we do not quote later, and otherwise
        # ansible gets it as "extra params".
        line='"VDSCLI_SSL_TIMEOUT = 120"',
    )


def test_he_deploy(
    root_dir,
    suite,
    ansible_host0,
    ansible_storage,
    he_host_name,
    he_mac_address,
    engine_ip,
    he_engine_answer_file_path,
):
    ansible_host0.copy(
        src=he_engine_answer_file_path,
        dest='/root/hosted-engine-deploy-answers-file.conf',
    )

    setup_file_src = os.path.join(root_dir, 'common/deploy-scripts/setup_first_he_host.sh')
    ansible_host0.copy(src=setup_file_src, dest='/root/', mode='preserve')

    ansible_host0.shell('/root/setup_first_he_host.sh ' f'{he_host_name} ' f'{he_mac_address} ' f'{engine_ip}')

    ansible_storage.shell('fstrim -va')


def test_set_global_maintenance(ansible_host0):
    logging.info('Waiting For System Stability...')
    he_utils.wait_until_engine_vm_is_not_migrating(ansible_host0)

    he_utils.set_and_test_global_maintenance_mode(ansible_host0, True)

    assert assert_utils.true_within_short(lambda: he_utils.all_hosts_state_global_maintenance(ansible_host0))
    logging.info('Global maintenance state set on all hosts')


def test_install_sar_collection(root_dir, ansible_engine, ost_images_distro):
    # TODO: Remove when we have an el9stream-based HE available
    if ost_images_distro == "el9stream":
        pytest.skip("el9stream packages are not installable on el8stream HE")

    ansible_engine.dnf(name='/var/tmp/lm_sensors.rpm', disable_gpg_check='yes')
    ansible_engine.dnf(name='/var/tmp/sysstat.rpm', disable_gpg_check='yes')
    ansible_engine.file(
        path='/etc/systemd/system/sysstat-collect.timer.d',
        state='directory',
    )
    sar_stat_src_dir = os.path.join(root_dir, 'common/sar_stat')
    ansible_engine.copy(
        src=os.path.join(sar_stat_src_dir, 'override.conf'),
        dest='/etc/systemd/system/sysstat-collect.timer.d',
    )
    ansible_engine.systemd(
        daemon_reload='yes',
        name='sysstat-collect.timer',
        state='started',
        enabled='yes',
    )


def test_check_installed_packages(request, ansible_all):
    if request.config.getoption('--skip-custom-repos-check'):
        pytest.skip('the check was disabled by the run argument')

    package_mgmt.check_installed_packages(ansible_all)
