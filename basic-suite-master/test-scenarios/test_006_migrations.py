#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import ipaddress
import json
import logging
import re
import uuid

from ovirtsdk4.types import (
    Host,
    NetworkUsage,
    VmStatus,
    Cluster,
    MigrationOptions,
    MigrationPolicy,
    ParallelMigrationsPolicy,
    Vm,
)

import pytest
from ost_utils import assert_utils
from ost_utils import network_utils
from ost_utils import test_utils

DC_NAME = 'test-dc'
CLUSTER_NAME = 'test-cluster'

NIC_NAME = 'enp1s0'
VLAN200_IF_NAME = f'{NIC_NAME}.200'

DEFAULT_MTU = 1500

LOGGER = logging.getLogger(__name__)

MIGRATION_NETWORK = 'Migration_Net'
MIGRATION_NETWORK_IPv4_ADDR = '192.0.3.{}'
MIGRATION_NETWORK_IPv4_MASK = '255.255.255.0'
MIGRATION_NETWORK_IPv6_ADDR = '1001:0db8:85a3:0000:0000:574c:14ea:0a0{}'
MIGRATION_NETWORK_IPv6_MASK = '64'

VM0_NAME = 'vm0'

VDSM_LOG = '/var/log/vdsm/vdsm.log'

EXPECTED_PARALLEL_CONNECTIONS = 2

VIR_MIGRATE_COMPRESSED = 2048
VIR_MIGRATE_PARALLEL = 131072

# Migration policy UUIDs are hard-coded
MIGRATION_POLICY_POSTCOPY = 'a7aeedb2-8d66-4e51-bb22-32595027ce71'
MIGRATION_POLICY_ZEROCOPY = '57237b82-b8c2-425f-b425-114b35219626'
MIGRATION_POLICY_SUSPEND_IF_NEEDED = '80554327-0569-496b-bdeb-fcbbf52b827c'


@pytest.fixture(scope="session")
def system_service(engine_api):
    return engine_api.system_service()


@pytest.fixture(scope="session")
def all_hosts_hostnames(system_service):
    hosts_service = system_service.hosts_service()
    return {host.name for host in hosts_service.list()}


@pytest.fixture(scope="module")
def prepare_migration_vlan(system_service):
    assert network_utils.set_network_usages_in_cluster(
        system_service,
        MIGRATION_NETWORK,
        CLUSTER_NAME,
        [NetworkUsage.MIGRATION],
    )

    # Set Migration_Network's MTU to match the other VLAN's on the NIC.
    assert network_utils.set_network_mtu(system_service, MIGRATION_NETWORK, DC_NAME, DEFAULT_MTU)


def migrate_vm(all_hosts_hostnames, ansible_by_hostname, system_service):
    vm_service = test_utils.get_vm_service(system_service, VM0_NAME)
    vm_id = vm_service.get().id
    hosts_service = system_service.hosts_service()

    def _current_running_host():
        host_id = vm_service.get().host.id
        host = hosts_service.list(search=f'id={host_id}')[0]
        return host.name

    src_host = _current_running_host()
    dst_host = next(iter(all_hosts_hostnames - {src_host}))

    LOGGER.debug(f'source host: {src_host}')
    LOGGER.debug(f'destination host: {dst_host}')

    correlation_id = uuid.uuid4()
    vm_service.migrate(host=Host(name=dst_host), query={'correlation_id': correlation_id})
    assert assert_utils.true_within_long(lambda: test_utils.all_jobs_finished(system_service, correlation_id))

    # Verify that VDSM cleaned the vm in the source host
    def vm_is_not_on_host():
        ansible_src_host = ansible_by_hostname(src_host)
        out = ansible_src_host.shell('vdsm-client Host getVMList')["stdout"]
        vms = json.loads(out)
        return vm_id not in [vm["vmId"] for vm in vms]

    assert assert_utils.true_within_short(vm_is_not_on_host)

    assert assert_utils.equals_within_short(lambda: vm_service.get().status, VmStatus.UP)

    assert _current_running_host() == dst_host

    return vm_id, src_host, dst_host


def prepare_migration_attachments_ipv4(system_service):
    hosts_service = system_service.hosts_service()

    for index, host in enumerate(test_utils.hosts_in_cluster_v4(system_service, CLUSTER_NAME), start=1):
        host_service = hosts_service.host_service(id=host.id)

        ip_address = MIGRATION_NETWORK_IPv4_ADDR.format(index)

        ip_configuration = network_utils.create_static_ip_configuration(
            ipv4_addr=ip_address, ipv4_mask=MIGRATION_NETWORK_IPv4_MASK
        )

        network_utils.attach_network_to_host(host_service, NIC_NAME, MIGRATION_NETWORK, ip_configuration)

        actual_address = next(
            nic for nic in host_service.nics_service().list() if nic.name == VLAN200_IF_NAME
        ).ip.address
        assert ipaddress.ip_address(actual_address) == ipaddress.ip_address(ip_address)


def prepare_migration_attachments_ipv6(system_service):
    hosts_service = system_service.hosts_service()

    for index, host in enumerate(test_utils.hosts_in_cluster_v4(system_service, CLUSTER_NAME), start=1):
        host_service = hosts_service.host_service(id=host.id)

        ip_address = MIGRATION_NETWORK_IPv6_ADDR.format(index)

        ip_configuration = network_utils.create_static_ip_configuration(
            ipv6_addr=ip_address, ipv6_mask=MIGRATION_NETWORK_IPv6_MASK
        )

        network_utils.modify_ip_config(system_service, host_service, MIGRATION_NETWORK, ip_configuration)

        actual_address = next(
            nic for nic in host_service.nics_service().list() if nic.name == VLAN200_IF_NAME
        ).ipv6.address
        assert ipaddress.ip_address(actual_address) == ipaddress.ip_address(ip_address)


def set_migration_policy(system_service, policy):
    cluster_service = test_utils.get_cluster_service(system_service, CLUSTER_NAME)
    cluster_service.update(cluster=Cluster(migration=MigrationOptions(policy=MigrationPolicy(id=policy))))


def set_vm_parallel_migrations(system_service, parallel_migrations_policy, custom_parallel_migrations=None):
    vm_service = test_utils.get_vm_service(system_service, VM0_NAME)
    vm_service.update(
        vm=Vm(
            migration=MigrationOptions(
                parallel_migrations_policy=parallel_migrations_policy,
                custom_parallel_migrations=custom_parallel_migrations,
            ),
        ),
    )


def migration_log_line(ansible_by_hostname, src_host, vm_id, dst_host_name):
    """Return the vdsm.log line of the last migration started on src_host.

    VDSM logs 'Migrating to ... with params ... and flags ...' right before
    calling libvirt's migrateToURI3, with all the migration parameters.
    Correlating on the VM id and destination host name keeps us safe from
    migrations of other VMs, which may run concurrently in the suite.
    """
    ansible_src_host = ansible_by_hostname(src_host)
    # '|| true' so that a missing match (grep rc=1) doesn't fail the ansible
    # command, but is instead handled by the assert below.
    pattern = f"'{vm_id}.*Migrating to .*{dst_host_name}'"
    out = ansible_src_host.shell(f"grep {pattern} {VDSM_LOG} || true")["stdout"]
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines, f'No migration log line found in {VDSM_LOG} on {src_host}'
    return lines[-1]


def verify_migration_flags(ansible_by_hostname, src_host, vm_id, dst_host_name, expected_flags):
    """Verify vdsm.log shows the migration was started with expected flags."""
    line = migration_log_line(ansible_by_hostname, src_host, vm_id, dst_host_name)
    LOGGER.debug(f'migration log line: {line}')
    flags_match = re.search(r'flags (\d+)', line)
    assert flags_match, f'No flags found in migration log line: {line}'
    flags = int(flags_match.group(1))
    assert flags & expected_flags == expected_flags, (
        f'Expected flags {expected_flags} (compressed={VIR_MIGRATE_COMPRESSED}, '
        f'parallel={VIR_MIGRATE_PARALLEL}) not all set in {flags} from line: {line}'
    )


def verify_parallel_connections(ansible_by_hostname, src_host, vm_id, dst_host_name):
    """Verify vdsm.log shows the migration used parallel connections."""
    line = migration_log_line(ansible_by_hostname, src_host, vm_id, dst_host_name)
    parallel_match = re.search(r"'parallel.connections': (\d+)", line)
    assert parallel_match, f'No parallel connections found in migration log line: {line}'
    parallel = int(parallel_match.group(1))
    assert (
        parallel == EXPECTED_PARALLEL_CONNECTIONS
    ), f'Expected {EXPECTED_PARALLEL_CONNECTIONS} parallel connections, got {parallel} in line: {line}'


def test_parallel_migration(
    all_hosts_hostnames,
    ansible_by_hostname,
    system_service,
    prepare_migration_vlan,
):
    prepare_migration_attachments_ipv4(system_service)
    set_migration_policy(system_service, MIGRATION_POLICY_SUSPEND_IF_NEEDED)
    set_vm_parallel_migrations(system_service, ParallelMigrationsPolicy.AUTO_PARALLEL)

    try:
        vm_id, src_host, dst_host_name = migrate_vm(all_hosts_hostnames, ansible_by_hostname, system_service)

        verify_parallel_connections(ansible_by_hostname, src_host, vm_id, dst_host_name)
        verify_migration_flags(
            ansible_by_hostname,
            src_host,
            vm_id,
            dst_host_name,
            VIR_MIGRATE_PARALLEL | VIR_MIGRATE_COMPRESSED,
        )
    finally:
        set_vm_parallel_migrations(system_service, ParallelMigrationsPolicy.INHERIT)


def test_ipv4_migration(
    all_hosts_hostnames,
    ansible_by_hostname,
    system_service,
    prepare_migration_vlan,
):
    prepare_migration_attachments_ipv4(system_service)
    set_migration_policy(system_service, MIGRATION_POLICY_ZEROCOPY)
    migrate_vm(all_hosts_hostnames, ansible_by_hostname, system_service)


def test_ipv6_migration(
    all_hosts_hostnames,
    ansible_by_hostname,
    system_service,
    prepare_migration_vlan,
):
    prepare_migration_attachments_ipv6(system_service)
    set_migration_policy(system_service, MIGRATION_POLICY_POSTCOPY)
    migrate_vm(all_hosts_hostnames, ansible_by_hostname, system_service)
