#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# -*- coding: utf-8 -*-
#

import ovirtsdk4 as sdk

from os import environ, path

from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.env import suite_dir
from ost_utils import engine_utils
from ost_utils import shell

def test_run_ocp_installer(ansible_engine, engine_api, engine_fqdn, engine_api_url,
                           engine_full_username, engine_password, suite_dir):

    working_dir = '/usr/local/bin'
    openshift_dir = '/usr/bin'
    dc_name = 'test-dc'
    cluster_name = 'test-cluster'
    sd_name = 'nfs'
    network_name = 'ovirtmgmt'
    ovirt_config = 'ovirt-config.yaml.in'
    install_config = 'install-config.yaml.in'
    script = 'test-run-ocp-installer.sh'
    ovirt_vnic_profile_id = ''
    sd_id = ''
    engine = engine_api.system_service()
    clusters_service = engine.clusters_service()
    cluster = clusters_service.list(search=f'name={cluster_name}')[0]
    cluster_id = cluster.id
    sds_service = engine.storage_domains_service()
    sds = sds_service.list(search=f'name={sd_name}')
    sd_id = next(iter([sd.id for sd in sds if sd.name == sd_name]))
    dc_id = next(iter(engine.data_centers_service().list(search=f'name={dc_name}'))).id
    networks = engine.networks_service().list(search=f'name={network_name}')
    network_id = next(iter([network.id for network in networks if network.data_center.id == dc_id]))
    ovirt_vnic_profile_id = engine.networks_service().network_service(network_id).vnic_profiles_service().list()[0].id
    src_script_file=os.path.join(
        suite_dir, ovirt_config
    )
    dst_script_file=os.path.join(
        working_dir, ovirt_config
    )
    ansible_engine.copy(
        src=src_script_file,
        dest=dst_script_file,
        mode='0666'
    )
    src_script_file=os.path.join(
        suite_dir, install_config
    )
    dst_script_file=os.path.join(
        working_dir, install_config
    )
    ansible_engine.copy(
        src=src_script_file,
        dest=dst_script_file,
        mode='0666'
    )
    src_script_file=os.path.join(
        suite_dir, script
    )
    dst_script_file=os.path.join(
        working_dir, script
    )
    ansible_engine.copy(
        src=src_script_file,
        dest=dst_script_file,
        mode='0755'
    )
    ansible_engine.shell(
        f'{dst_script_file} '
        f'-c {cluster_id} '
        f'-s {sd_id} '
        f'-w {working_dir} '
        f'-o {openshift_dir} '
        f'-a {engine_api_url} '
        f'-u {engine_full_username} '
        f'-p {engine_password} '
        '-k /etc/ssh/ssh_host_rsa_key.pub '
        '-r tr '
        f'-n {network_name} '
        f'-v {ovirt_vnic_profile_id} '
        f'-d {engine_fqdn}'
    )
