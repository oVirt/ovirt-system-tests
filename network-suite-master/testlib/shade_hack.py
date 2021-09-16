#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
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

    return cloud.network.put(
        path,
        json=data,
        error_message='Error in PUT request: {path}'.format(path=path),
    )
