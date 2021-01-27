#
# Copyright 2017-2021 Red Hat, Inc.
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
