#
# Copyright 2019 Red Hat, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from __future__ import absolute_import
from __future__ import print_function

import sys

from textwrap import dedent

import six

from lago import sdk


def usage():
    msg = \
        """
        Usage: find_ipv6_subnet PREFIX_PATH NETWORK_NAME

        Finds the IPv6 subnet and exports it as IPV6_SUBNET env variable
        to all vms

        PREFIX_PATH is a path to a lago prefix.
        NETWORK_NAME name of the network to search for subnet
        """
    print(dedent(msg))


def find_ipv6_subnet(prefix, network_name):
    net = prefix.get_nets().get(network_name)
    subnet = get_subnet_from_ipv4(net.gw())
    return subnet


def set_subnet_env_var_for_vms(prefix, subnet):
    vms = [vm for vm in six.viewvalues(prefix.get_vms()) if
           vm.vm_type != 'ovirt-engine']
    ipv6_subnet = '"export IPV6_SUBNET=%s"' % subnet
    for vm in vms:
        vm.ssh(['echo', ipv6_subnet, '>>', '$HOME/.bashrc'])


def get_subnet_from_ipv4(ip):
    # We need this hack to figure out what is the dynamically created subnet
    # for the IPv6 network
    return ip.split('.')[2]


def main():
    if len(sys.argv) != 3:
        usage()
        sys.exit(1)
    prefix = sdk.load_env(sys.argv[1])
    subnet = find_ipv6_subnet(prefix, network_name=sys.argv[2])
    set_subnet_env_var_for_vms(prefix, subnet)
    print(subnet)


if __name__ == '__main__':
    main()
