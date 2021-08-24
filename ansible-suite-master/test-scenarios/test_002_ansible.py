#
# Copyright 2021 Red Hat, Inc.
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

from ost_utils.ansible.collection import CollectionMapper, infra
from ost_utils.storage_utils import lun


def test_ansible_run(ansible_engine, hostnames_to_add, engine_storage_ips):
    infra(
        ansible_engine=ansible_engine,
        engine_fqdn="localhost",
        engine_user="admin@internal",
        engine_password="123",
        engine_cafile="/etc/pki/ovirt-engine/ca.pem",
        data_center_name="test-dc",
        compatibility_version=4.4,
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
                    "address": engine_storage_ips[0],
                    "path": "/exports/nfs/share1",
                },
            },
            "second-nfs": {
                "state": "present",
                "nfs": {
                    "address": engine_storage_ips[0],
                    "path": "/exports/nfs/share2",
                },
            },
            "templates": {
                "domain_function": "export",
                "nfs": {
                    "address": engine_storage_ips[0],
                    "path": "/exports/nfs/exported",
                },
            },
            "iso": {
                "domain_function": "iso",
                "nfs": {
                    "address": engine_storage_ips[0],
                    "path": "/exports/nfs/iso",
                },
            },
            "iscsi": {
                "iscsi": {
                    "target": "iqn.2014-07.org.ovirt:storage",
                    "port": 3260,
                    "address": engine_storage_ips[0],
                    "username": "username",
                    "password": "password",
                    "lun_id": lun.get_uuids(ansible_engine)[:2],
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
        url="https://localhost/ovirt-engine/api",
        username="admin@internal",
        password="123",
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
