#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import ipaddress
import os
import random
import tempfile

import pytest

from ost_utils.ansible import facts
from ost_utils.backend.virsh import network
from ost_utils.storage_utils import lun

PROFILE_PCI_DSS = 'pci-dss'
PROFILE_STIG = 'stig'


@pytest.fixture(scope="session")
def he_mac_address():
    return '54:52:{}'.format(':'.join(('{:02x}'.format(random.randrange(255)) for i in range(4))))


# FIXME this is not a good idea when there are multiple networks currently, as
# the ansible_default_ipv4 returns IP form a random gateway, and currently all
# OST networks result in a gateway for that particular network. It should
# return IP on the management network only
@pytest.fixture(scope="session")
def he_ipv4_address(ansible_host0_facts):
    host0_ipv4 = ansible_host0_facts.get('ansible_default_ipv4').get('address')
    res = None
    if host0_ipv4:
        res = '{prefix}.{suffix}'.format(
            prefix='.'.join(host0_ipv4.split('.')[:3]),
            suffix=random.randrange(50, 100),
        )
    return res


# FIXME this is not a good idea when there are multiple networks currently, as
# the ansible_default_ipv6 returns IP form a random gateway, and currently all
# OST networks result in a gateway for that particular network. It should
# return IP on the management network only
@pytest.fixture(scope="session")
def he_ipv6_address(ansible_host0_facts):
    host0_ipv6 = ansible_host0_facts.get('ansible_default_ipv6').get('address')
    res = None
    if host0_ipv6:
        *prefix, lasthextet = host0_ipv6.split(':')
        res = '{prefix}:{prelast}63'.format(
            prefix=':'.join(prefix),
            prelast=lasthextet[:2],
        )
    return res


@pytest.fixture(scope="session")
def he_host_name(backend):
    return '{}-engine'.format('-'.join(backend.storage_hostname().split('-')[:-1]))


@pytest.fixture(scope="session")
def ansible_he(
    management_network_name,
    ansible_inventory,
    backend,
    he_mac_address,
    he_ip_address,
    he_ipv4_address,
    he_ipv6_address,
    he_host_name,
    ansible_by_hostname,
):
    network.add_name(
        libvirt_net_name=backend.libvirt_net_name(management_network_name),
        host_name=he_host_name,
        mac_address=he_mac_address,
        ipv4_address=he_ipv4_address,
        ipv6_address=he_ipv6_address,
    )
    ssh_key_file = os.environ.get('OST_IMAGES_SSH_KEY')
    ansible_inventory.add(
        he_host_name,
        (
            '[default]\n'
            f'{he_host_name} '
            f'ansible_host={he_ip_address} '
            f'ansible_ssh_private_key_file={ssh_key_file}\n'
        ).encode(),
    )
    return ansible_by_hostname(he_host_name)


@pytest.fixture(scope="session")
def ansible_he_facts(ansible_he):
    return facts.Facts(ansible_he)


@pytest.fixture(scope="session")
def he_ip_prefix(backend, he_ipv6_address):
    if he_ipv6_address:
        return backend.get_ip_prefix_for_management_network(6)
    return backend.get_ip_prefix_for_management_network(4)


@pytest.fixture(scope="session")
def he_domain_name(ansible_host0_facts):
    return ansible_host0_facts.get('ansible_domain')


@pytest.fixture(scope="session")
def he_interface(ansible_host0_facts):
    if ansible_host0_facts.get('ansible_default_ipv6'):
        return ansible_host0_facts.get('ansible_default_ipv6').get('interface')
    return ansible_host0_facts.get('ansible_default_ipv4').get('interface')


@pytest.fixture(scope="session")
def he_ip_address(he_ipv4_address, he_ipv6_address):
    # This follows the same preference as DNS resolution
    if he_ipv6_address:
        return he_ipv6_address
    return he_ipv4_address


@pytest.fixture(scope="session")
def he_lun_id(ansible_storage):
    return lun.get_he_uuids(ansible_storage)[0]


@pytest.fixture(scope="session")
def he_engine_answer_file_storage_snippet(
    storage_hostname,
    sd_iscsi_host_ip,
    he_lun_id,
    ost_he_storage_domain_type,
):
    if ost_he_storage_domain_type == 'nfs':
        return (
            'OVEHOSTED_STORAGE/domainType=str:nfs3\n'
            'OVEHOSTED_STORAGE/storageDomainConnection=str:'
            f'{storage_hostname}:/exports/nfs_he\n'
        )
    elif ost_he_storage_domain_type == 'iscsi':
        return (
            'OVEHOSTED_STORAGE/domainType=str:iscsi\n'
            'OVEHOSTED_STORAGE/iSCSIPortalIPAddress=str:'
            f'{sd_iscsi_host_ip}\n'
            'OVEHOSTED_STORAGE/LunID=str:'
            f'{he_lun_id}\n'
        )
    else:
        raise RuntimeError(f'Unknown ost_he_storage_domain_type {ost_he_storage_domain_type}')


@pytest.fixture(scope="session")
def he_engine_answer_file_openscap_profile_snippet(ansible_host0):
    profile = ansible_host0.shell('cat /root/ost_images_openscap_profile')['stdout']
    if len(profile) > 0:
        he_profile = PROFILE_PCI_DSS if PROFILE_PCI_DSS in profile else PROFILE_STIG
        return 'OVEHOSTED_VM/applyOpenScapProfile=bool:True\n' f'OVEHOSTED_VM/OpenScapProfileName=str:{he_profile}\n'
    else:
        return 'OVEHOSTED_VM/applyOpenScapProfile=bool:False\n'


@pytest.fixture(scope="session")
def he_engine_answer_file_keycloak_snippet(keycloak_enabled):
    val = 'True' if keycloak_enabled else 'False'
    return f'OVEHOSTED_CORE/enableKeycloak=bool:{val}\n'


@pytest.fixture(scope="session")
def he_engine_answer_file_contents(
    he_host_name,
    he_domain_name,
    he_interface,
    management_gw_ip,
    host0_hostname,
    storage_hostname,
    he_mac_address,
    he_ip_address,
    he_ip_prefix,
    engine_password,
    root_password,
    he_engine_answer_file_storage_snippet,
    he_engine_answer_file_openscap_profile_snippet,
    he_engine_answer_file_keycloak_snippet,
):
    return (
        '[environment:init]\n'
        'DIALOG/autoAcceptDefault=bool:True\n'
        '[environment:default]\n'
        'OVEHOSTED_CORE/screenProceed=bool:True\n'
        'OVEHOSTED_CORE/deployProceed=bool:True\n'
        'OVEHOSTED_CORE/confirmSettings=bool:True\n'
        'OVEHOSTED_CORE/skipTTYCheck=bool:True\n'
        f'OVEHOSTED_NETWORK/fqdn=str:{he_host_name}.{he_domain_name}\n'
        f'OVEHOSTED_NETWORK/bridgeIf=str:{he_interface}\n'
        'OVEHOSTED_NETWORK/firewallManager=str:iptables\n'
        f'OVEHOSTED_NETWORK/gateway=str:{str(management_gw_ip)}\n'
        f'OVEHOSTED_ENGINE/adminPassword=str:{engine_password}\n'
        f'OVEHOSTED_ENGINE/appHostName=str:{host0_hostname}.'
        f'{he_domain_name}\n'
        'OVEHOSTED_STORAGE/storageDatacenterName=str:hosted_datacenter\n'
        'OVEHOSTED_STORAGE/storageDomainName=str:hosted_storage\n'
        'OVEHOSTED_VM/vmMemSizeMB=int:3171\n'
        'OVEHOSTED_CORE/memCheckRequirements=bool:False\n'
        f'OVEHOSTED_VM/vmMACAddr=str:{he_mac_address}\n'
        'OVEHOSTED_VM/vmVCpus=str:2\n'
        f'OVEHOSTED_VM/cloudinitInstanceDomainName=str:{he_domain_name}\n'
        f'OVEHOSTED_VM/cloudinitInstanceHostName=str:{he_host_name}.'
        f'{he_domain_name}\n'
        f'OVEHOSTED_VM/cloudinitVMStaticCIDR=str:{he_ip_address}'
        f'/{he_ip_prefix}\n'
        f'OVEHOSTED_VM/cloudinitRootPwd=str:{root_password}\n'
        'OVEHOSTED_VM/cloudinitVMETCHOSTS=bool:True\n'
        f'OVEHOSTED_VM/cloudinitVMDNS=str:{str(management_gw_ip)}\n'
        'OVEHOSTED_VM/rootSshAccess=str:yes\n'
        'OVEHOSTED_VM/rootSshPubkey=str:\n'
        'OVEHOSTED_VDSM/cpu=str:model_SandyBridge\n'
        f'{he_engine_answer_file_storage_snippet}'
        'OVEHOSTED_CORE/ansibleUserExtraVars=str:he_offline_deployment=true\n'
        f'{he_engine_answer_file_openscap_profile_snippet}'
        f'{he_engine_answer_file_keycloak_snippet}'
    )


@pytest.fixture(scope="session")
def he_engine_answer_file_path(he_engine_answer_file_contents):
    with tempfile.NamedTemporaryFile(mode="w+t") as tmp:
        tmp.writelines(he_engine_answer_file_contents)
        tmp.flush()
        yield tmp.name
