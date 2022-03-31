#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import os


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
    ansible_vms_to_deploy,
):
    conspath = ansible_host0.shell(
        "python3 -c " "'from ovirt_hosted_engine_ha.env import constants; " "print(constants.__file__)'"
    )['stdout_lines'][0]
    ansible_vms_to_deploy.lineinfile(
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

    bck_file = os.path.join(root_dir, 'common/he-engine-dc1-cl1.bck')
    ansible_host0.copy(src=bck_file, dest='/root/', mode='preserve')

    ansible_host0.shell('/root/setup_first_he_host.sh ' f'{he_host_name} ' f'{he_mac_address} ' f'{engine_ip}')

    ansible_storage.shell('fstrim -va')


def test_install_sar_collection(root_dir, ansible_engine):
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


def test_add_engine_to_artifacts(artifacts, he_host_name, artifact_list):
    artifacts[he_host_name] = artifact_list
