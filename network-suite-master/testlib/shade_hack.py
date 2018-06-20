#
# Copyright 2018 Red Hat, Inc.
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


# HACK: avoid using this unless absolutelly required!
# This is a placeholder for missing shade functionality
# Because of functionality gaps in shade we are using internal shade
# _network_client to manually contruct the required query.
# The alternative would be to handle openstack authentication, path lookup,
# etc. manually. Here the cost is accessing _network_client
# For each use please file a shade bug to extend shade functionality.
# current bugs: BZ 1590248

def hack_os_put_request(cloud, path, data):

    return cloud._network_client.put(
        path, json=data,
        error_message='Error in PUT request: {path}'.format(path=path))
