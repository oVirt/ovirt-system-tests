#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import ipaddress

from ovirtsdk4.types import (
    BootProtocol,
    DataCenter,
    HostNic,
    Ip,
    IpAddressAssignment,
    IpVersion,
    Network,
    NetworkAttachment,
    Cluster,
    VnicProfile,
    Nic,
)

from ost_utils import constants
from ost_utils import test_utils


def get_ips(backend, ansible_facts, network_name):
    hostname = ansible_facts.get("ansible_hostname")

    return [str(ip) for ip in backend.ips_for(hostname, network_name)]


def ip_to_url(ip):
    return f'[{ip}]' if ipaddress.ip_address(ip).version == 6 else ip


def _get_attachment_by_id(host, network_id):
    return next(att for att in host.network_attachments_service().list() if att.network.id == network_id)


def attach_network_to_host(host, nic_name, network_name, ip_configuration, bonds=[]):
    attachment = NetworkAttachment(
        network=Network(name=network_name),
        host_nic=HostNic(name=nic_name),
        ip_address_assignments=ip_configuration,
    )

    return host.setup_networks(
        modified_bonds=bonds,
        modified_network_attachments=[attachment],
        check_connectivity=True,
    )


def modify_ip_config(engine, host, network_name, ip_configuration):
    query = f'name={test_utils.quote_search_string(network_name)}'

    network_id = engine.networks_service().list(search=query)[0].id

    attachment = _get_attachment_by_id(host, network_id)
    attachment.ip_address_assignments = ip_configuration

    return host.setup_networks(modified_network_attachments=[attachment], check_connectivity=True)


def create_static_ip_configuration(ipv4_addr=None, ipv4_mask=None, ipv6_addr=None, ipv6_mask=None):
    assignments = []
    if ipv4_addr:
        assignments.append(
            IpAddressAssignment(
                assignment_method=BootProtocol.STATIC,
                ip=Ip(address=ipv4_addr, netmask=ipv4_mask),
            )
        )
    if ipv6_addr:
        assignments.append(
            IpAddressAssignment(
                assignment_method=BootProtocol.STATIC,
                ip=Ip(address=ipv6_addr, netmask=ipv6_mask, version=IpVersion.V6),
            )
        )

    return assignments


def get_network_attachment(engine, host, network_name, dc_name):
    dc = test_utils.data_center_service(engine, dc_name)

    # CAVEAT: .list(search='name=Migration_Network') is ignored, and the first
    #         network returned happened to be VM_Network in my case
    network = next(net for net in dc.networks_service().list() if net.name == network_name)

    return _get_attachment_by_id(host, network.id)


def set_network_usages_in_cluster(engine, network_name, cluster_name, usages):
    cluster_service = test_utils.get_cluster_service(engine, cluster_name)
    query = f'name={test_utils.quote_search_string(network_name)}'

    network = engine.networks_service().list(search=query)[0]
    network_service = cluster_service.networks_service().network_service(id=network.id)

    network.usages = usages

    return network_service.update(network)


def set_network_mtu(engine, network_name, dc_name, mtu):
    dc = test_utils.data_center_service(engine, dc_name)

    network = next(net for net in dc.networks_service().list() if net.name == network_name)
    network_service = dc.networks_service().network_service(id=network.id)

    network.mtu = mtu

    return network_service.update(network)


def create_network_params(network_name, dc_name, **net_params):
    return Network(
        name=network_name,
        data_center=DataCenter(
            name=dc_name,
        ),
        **net_params,
    )


def get_default_ovn_provider_id(engine):
    service = engine.openstack_network_providers_service()
    for provider in service.list():
        if provider.name == constants.DEFAULT_OVN_PROVIDER_NAME:
            return provider.id
    raise RuntimeError(f'{constants.DEFAULT_OVN_PROVIDER_NAME} not present in oVirt')


def add_networks(engine, dc_name, cluster_name, network_names):
    networks_service = engine.networks_service()
    networks = []
    for net_name in network_names:
        network = networks_service.add(
            network=Network(
                name=net_name,
                data_center=DataCenter(name=dc_name),
                cluster=Cluster(name=cluster_name),
            )
        )
        networks.append(network)
    return networks


def assign_networks_to_cluster(engine, cluster_name, networks, required):
    service = _get_cluster_network_service(engine, cluster_name)
    for network in networks:
        service.add(network=Network(id=network.id, required=required))


def _get_network(engine, cluster_name, network_name):
    cns = _get_cluster_network_service(engine, cluster_name)
    return _filter_named_item(network_name, cns.list())


def get_profiles_for(engine, networks):
    profiles = []
    profile_service = engine.vnic_profiles_service()
    network_ids = [network.id for network in networks]
    for profile in profile_service.list():
        if profile.network.id in network_ids:
            profiles.append(profile)
    return profiles


def get_profile_by_name(engine, cluster_name, network_name, profile_name):
    network = _get_network(engine, cluster_name, network_name)
    profiles = get_profiles_for(engine, [network])
    return next((p for p in profiles if p.name == profile_name), None)


def get_profile_for_id(engine, profile_id):
    return engine.vnic_profiles_service().profile_service(profile_id).get()


def nic_with_profile():
    return lambda n: n.vnic_profile is not None


def filter_nics_with_profiles(nics):
    return filter(nic_with_profile(), nics)


def create_nics_on_vm(engine, vm_name, profiles):
    vm2_service = test_utils.get_vm_service(engine, vm_name)
    _add_nics(vm2_service, profiles)


def _add_nics(vm_service, profiles):
    nics_service = vm_service.nics_service()
    for profile in profiles:
        nics_service.add(Nic(name=profile.name, vnic_profile=VnicProfile(id=profile.id)))


def get_nics_on(engine, vm_name):
    return test_utils.get_vm_service(engine, vm_name).nics_service().list()


def _get_cluster_network_service(engine, cluster_name):
    cluster_service = test_utils.get_cluster_service(engine, cluster_name)
    return cluster_service.networks_service()


def remove_profiles(engine, profiles, predicate):
    to_remove = filter(predicate, profiles)
    for profile in to_remove:
        engine.vnic_profiles_service().profile_service(profile.id).remove()


def remove_networks(engine, networks, predicate):
    to_remove = filter(predicate, networks)
    for network in to_remove:
        engine.networks_service().network_service(network.id).remove()


def _filter_named_item(name, collection):
    return next(item for item in collection if item.name == name)
