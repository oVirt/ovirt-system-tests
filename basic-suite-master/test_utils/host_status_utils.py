#
# Copyright 2017 Red Hat, Inc.
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

DC_NAME = 'test-dc'

def _host_status_to_print(hosts_service, hosts_list):
    dump_hosts = ''
    for host in hosts_list:
            host_service_info = hosts_service.host_service(host.id)
            dump_hosts += '%s: %s\n' % (host.name, host_service_info.get().status)
    return dump_hosts


def _hosts_in_dc(api, dc_name=DC_NAME, random_host=False):
    hosts_service = api.system_service().hosts_service()
    all_hosts = _wait_for_status(hosts_service, dc_name, types.HostStatus.UP)
    up_hosts = [host for host in all_hosts if host.status == types.HostStatus.UP]
    if up_hosts:
        if random_host:
            return random.choice(up_hosts)
        else:
            return sorted(up_hosts, key=lambda host: host.name)
    hosts_status = [host for host in all_hosts if host.status != types.HostStatus.UP]
    dump_hosts = _host_status_to_print(hosts_service, hosts_status)
    raise RuntimeError('Could not find hosts that are up in DC {} \nHost status: {}'.format(dc_name, dump_hosts) )


def _random_host_from_dc(api, dc_name=DC_NAME):
    return _hosts_in_dc(api, dc_name, True)


def _random_host_service_from_dc(api, dc_name=DC_NAME):
    host = _hosts_in_dc(api, dc_name, True)
    return api.system_service().hosts_service().host_service(id=host.id)


def _all_hosts_up(hosts_service, total_num_hosts, dc_name=DC_NAME):
    installing_hosts = hosts_service.list(search='datacenter={} AND status=installing or status=initializing'.format(dc_name))
    if len(installing_hosts) == total_num_hosts: # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(dc_name))
    if len(up_hosts) == total_num_hosts:
        return True

    _check_problematic_hosts(hosts_service, dc_name)


def _single_host_up(hosts_service, total_num_hosts, dc_name=DC_NAME):
    installing_hosts = hosts_service.list(search='datacenter={} AND status=installing or status=initializing'.format(dc_name))
    if len(installing_hosts) == total_num_hosts : # All hosts still installing
        return False

    up_hosts = hosts_service.list(search='datacenter={} AND status=up'.format(dc_name))
    if len(up_hosts):
        return True

    _check_problematic_hosts(hosts_service, dc_name)


def _check_problematic_hosts(hosts_service, dc_name=DC_NAME):
    problematic_hosts = hosts_service.list(search='datacenter={} AND status != installing and status != initializing and status != up)'.format(dc_name))
    if len(problematic_hosts):
        dump_hosts = '%s hosts failed installation:\n' % len(problematic_hosts)
        for host in problematic_hosts:
            host_service = hosts_service.host_service(host.id)
            dump_hosts += '%s: %s\n' % (host.name, host_service.get().status)
        raise RuntimeError(dump_hosts)
