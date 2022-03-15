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
    storage_hostname,
    sd_iscsi_host_ip,
    engine_full_username,
    engine_password,
    sd_iscsi_ansible_host,
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
                "cpu_arch": "ppc64",
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
                    "address": storage_hostname,
                    "path": "/exports/nfs/share1",
                    "version": "v4_2",
                },
            },
            "second-nfs": {
                "state": "present",
                "nfs": {
                    "address": storage_hostname,
                    "path": "/exports/nfs/share2",
                    "version": "v4_2",
                },
            },
            "templates": {
                "domain_function": "export",
                "nfs": {
                    "address": storage_hostname,
                    "path": "/exports/nfs/exported",
                    "version": "v4_2",
                },
            },
            "iso": {
                "domain_function": "iso",
                "nfs": {
                    "address": storage_hostname,
                    "path": "/exports/nfs/iso",
                    "version": "v4_2",
                },
            },
            "iscsi": {
                "iscsi": {
                    "target": "iqn.2014-07.org.ovirt:storage",
                    "port": 3260,
                    "address": storage_hostname,
                    "username": "username",
                    "password": "password",
                    "lun_id": lun.get_uuids(sd_iscsi_ansible_host)[:2],
                }
            },
        },
        logical_networks=[
            {
                "name": "Migration_Net",
                "description": "Non VM Network on VLAN 200, MTU 9000",
                "mtu": 9000,
                "vlan_tag": 200,
                "clusters": [
                    {
                        "name": "test-cluster",
                        "assigned": True,
                        "migration": True,
                        "required": False,
                        "display": False,
                        "gluster": False,
                    }
                ],
            }
        ],
        mac_pools=[
            {
                "mac_pool_name": "mymacpool",
                "mac_pool_ranges": [
                    "02:00:00:00:00:00,02:00:00:01:00:00",
                ],
            }
        ],
    )

    collection = CollectionMapper(ansible_engine)

    ovirt_auth = collection.ovirt_auth(
        hostname=engine_ip_url,
        username=engine_full_username,
        password=engine_password,
        insecure="true",
    )['ansible_facts']['ovirt_auth']

    collection.ovirt_host_info(auth=ovirt_auth, pattern="name=*")

    collection.ovirt_vm(
        auth=ovirt_auth,
        name="rhel",
        cluster="test-cluster",
        memory="1GiB",
        cloud_init={"user_name": 'root', 'root_password': 'super_password'},
        cloud_init_persist="true",
    )

    # Revoke the SSO token
    collection.ovirt_auth(
        state="absent",
        ovirt_auth=ovirt_auth,
    )
