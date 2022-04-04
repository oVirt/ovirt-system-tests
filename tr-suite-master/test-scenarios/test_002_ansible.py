#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

from ost_utils.ansible.collection import CollectionMapper, infra
from ost_utils.storage_utils import lun


def test_ansible_run(
    ansible_engine,
    hostnames_to_add,
    engine_ip_url,
    engine_fqdn,
    engine_storage_ips,
    engine_full_username,
    engine_password,
):
    infra(
        ansible_engine,
        engine_fqdn=engine_ip_url,
        engine_user=engine_full_username,
        engine_password=engine_password,
        engine_cafile="/etc/pki/ovirt-engine/ca.pem",
        data_center_name="test-dc",
        compatibility_version=4.4,
        ansible_async_dir='/home/runner/.ansible_async',
        clusters=[
            {
                "name": "test-cluster",
                "description": "APIv4 Cluster",
                "scheduling_policy": "evenly_distributed",
                "profile": "my_cpu_profile",
                "cpu_arch": "x86_64",
                "cpu_type": "",
                "ksm": "yes",
                "ksm_numa": "yes",
                "memory_policy": "server",
                "ha_reservation": "yes",
                "vm_reason": "yes",
                "ballooning": "yes",
                "external_network_providers": [
                    {
                        "name": "ovirt-provider-ovn",
                    },
                ],
            },
        ],
        hosts=[
            {
                "name": host,
                "address": host,
                "cluster": "test-cluster",
                "password": "123456",
                "description": f"host {host}",
                "power_management": {
                    "address": '1.2.3.4',
                    "state": "present",
                    "type": 'ipmilan',
                    "username": 'myusername',
                    "password": 'mypassword',
                    "options": {
                        "myname": 'myvalue',
                    },
                    "order": 0,
                },
            }
            for host in hostnames_to_add
        ],
        storages={
            "nfs": {
                "master": "true",
                "state": "present",
                "nfs": {
                    "address": engine_fqdn,
                    "path": "/exports/nfs/share1",
                    "version": "v4_2",
                },
            },
        },
        mac_pools=[
            {
                "mac_pool_name": "mymacpool",
                "mac_pool_ranges": [
                    "02:00:00:00:00:00,02:00:00:01:00:00",
                ],
            }
        ],
    )
