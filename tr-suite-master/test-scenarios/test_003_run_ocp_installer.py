# -*- coding: utf-8 -*-
#
# Copyright 2014, 2017, 2019 Red Hat, Inc.
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

import ovirtsdk4 as sdk

from os import environ, path

from ost_utils.pytest.fixtures.engine import *
from ost_utils.pytest.fixtures.env import suite_dir
from ost_utils import engine_utils
from ost_utils import shell

def test_run_ocp_installer(ansible_engine, engine_api, engine_fqdn, engine_api_url,
                           engine_full_username, engine_password, suite_dir):

    working_dir = '/tmp'
    cluster_name = 'test-cluster'
    sd_name = 'nfs'
    network_name = 'ovirtmgmt'
    ovirt_config = 'ovirt-config.yaml.in'
    install_config = 'install-config.yaml.in'
    script = 'test-run-ocp-installer.sh'
    ovirt_vnic_profile_id = ''
    engine = engine_api.system_service()
    clusters_service = engine.clusters_service()
    cluster = clusters_service.list(search=f'name={cluster_name}')[0]
    cluster_id = cluster.id
    sds_service = engine.storage_domains_service()
    sd = sds_service.list(search=f'name={sd_name}')[0]
    sd_id = sd.id
    vnic_profiles_service = engine.vnic_profiles_service()
    vnic_profiles = vnic_profiles_service.list(search=f'name={network_name}')
    # Get vNic id by its name using a loop since search is not supported and returns all
    for vnic_profile in vnic_profiles:
        if vnic_profile.name == network_name:
            ovirt_vnic_profile_id = vnic_profile.id
            break


    # get PR number from the env if not found then use master branch
    pr = os.environ.get('STD_CI_REFSPEC')
    if pr == None or not pr:
        pr = "master"

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
        '-w /tmp '
        f'-a {engine_api_url} '
        f'-u {engine_full_username} '
        f'-p {engine_password} '
        '-k /etc/ssh/ssh_host_rsa_key.pub '
        '-r tr '
        f'-n {network_name} '
        f'-v {ovirt_vnic_profile_id} '
        f'-t {pr} '
        f'-d {engine_fqdn}'
    )
