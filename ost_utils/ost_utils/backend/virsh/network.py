#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging

from ost_utils import shell


LOGGER = logging.getLogger(__name__)


def add_name(
    libvirt_net_name,
    host_name,
    mac_address,
    ipv4_address=None,
    ipv6_address=None,
):
    def run_net_update_add(*extra_args):
        cmd = (
            'virsh',
            '-c',
            'qemu:///system',
            'net-update',
            libvirt_net_name,
            'add',
        ) + extra_args
        try:
            shell.shell(cmd)
        except shell.ShellError:
            # TODO: Optionally/Conditionally fail.
            # Why not to always fail? Because it's comfortable to be able to
            # retry stuff with lagofy.sh/run_tc.
            # So need to do one or more of:
            # 1. Check if exists, do not try to add
            # 2. Remove and then add?
            # 3. raise an exception and let caller catch/handle
            # 4. Let caller decide whether we fail
            LOGGER.warn(f"Failed '{cmd}', ignoring", exc_info=True)

    def run_net_update_add_dns(name, ip):
        run_net_update_add(
            'dns-host',
            (f"<host ip='{ip}'> " f"  <hostname>{name}</hostname> " "</host>"),
            '--live',
        )

    if ipv4_address is not None:
        run_net_update_add(
            'ip-dhcp-host',
            (
                "<host "
                f"mac='{mac_address}' "
                f"name='{host_name}' "
                f"ip='{ipv4_address}' "
                "/>"
            ),
            '--live',
        )
        run_net_update_add_dns(host_name, ipv4_address)
    if ipv6_address is not None:
        run_net_update_add(
            'ip-dhcp-host',
            (
                "<host "
                f"id='0:3:0:1:{mac_address}' "
                f"name='{host_name}' "
                f"ip='{ipv6_address}' "
                "/>"
            ),
            '--live',
            '--parent-index',
            '1',
        )
        run_net_update_add_dns(host_name, ipv6_address)
