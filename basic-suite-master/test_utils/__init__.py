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

def hosts_in_cluster_v3(api, cluster_name):
    hosts = api.hosts.list(query='cluster={}'.format(cluster_name))
    return sorted(hosts, key=lambda host: host.name)


def hosts_in_cluster_v4(root, cluster_name):
    hosts = root.hosts_service().list(search='cluster={}'.format(cluster_name))
    return sorted(hosts, key=lambda host: host.name)


def data_center_service(root, name):
    data_centers = root.data_centers_service()
    dc = data_centers.list(search='name={}'.format(name))[0]
    return data_centers.data_center_service(dc.id)
