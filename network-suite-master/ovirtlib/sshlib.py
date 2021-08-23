# Copyright 2018-2021 Red Hat, Inc.
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
import ipaddress
import logging
import paramiko
import pytest

from ovirtlib import syncutil

DEFAULT_USER = 'root'
ROOT_PASSWORD = '123456'
TIMEOUT = 60 * 5

logging.getLogger('paramiko.transport').setLevel(logging.WARNING)


class SshException(Exception):
    pass


class Node(object):
    """
    A class to collect operations that need to be carried out on a node (host
    or VM) but are not supported by the corresponding oVirt objects.
    """

    def __init__(self, address, password=ROOT_PASSWORD, username=DEFAULT_USER):
        """
        :param address: address of the endpoint
        :param password: the password
        :param username: the username, root if not specified
        """
        self._address = address
        self._username = username
        self._password = password
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy())

    def exec_command(self, command):
        """
        Execute a ssh command on a host
        :param command: command to be executed
        :returns stdout: the standard output of the command
        :raises exc: Exception: if the command returns a non-zero exit status
        """
        self._connect()
        try:
            _, stdout, stderr = self._client.exec_command(command)
            status = stdout.channel.recv_exit_status()
            stdout_message = stdout.read()
            if status != 0:
                stderr_message = stderr.read()
                raise SshException(
                    f'Ssh command "{command}" exited with '
                    f'status code {status}. '
                    f'Stderr: {stderr_message}. '
                    f'Stdout: {stdout_message}. '
                )
            return stdout_message
        finally:
            self._close()

    def sftp_put(self, local_path, remote_path):
        self._connect()
        sftp = paramiko.SFTPClient.from_transport(self._client.get_transport())
        try:
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()
            self._close()

    def _connect(self):
        self._client.connect(self._address, username=self._username,
                             password=self._password)

    def _close(self):
        self._client.close()

    def set_mtu(self, iface_name, mtu_value):
        self.exec_command('ip link set {iface} mtu {mtu}'
                          .format(iface=iface_name, mtu=mtu_value))

    def change_active_slave(self, bond_name, slave_name):
        """"
        :param bond_name: str
        :param slave_name: str
        """
        self.exec_command(
            'ip link set {bond} type bond active_slave {slave}'.format(
                bond=bond_name, slave=slave_name
            )
        )

    def assert_default_route(self, expected_v6_route_address):
        assert expected_v6_route_address == self.get_default_route_v6()

    def get_default_route_v6(self):
        """
        :return: the v6 default route as string or None
        """
        return self._get_default_route('inet6')

    def _get_default_route(self, family):
        """
        :param family: inet for ipv4 or inet6 for ipv6
        :return: the default route address as string or None
        """
        command = 'ip -o -f ' + family + ' r show default'
        res = self.exec_command(command)
        if res is not None:
            res = res[(res.find('via ') + len('via ')):res.find(' dev')]
        return res

    def assert_no_ping_from_netns(self, target, from_netns):
        with pytest.raises(SshException, match='100% packet loss'):
            self.ping_from_netns(target=target, from_netns=from_netns)

    def assert_ping_from_netns(self, target, from_netns):
        self.ping_from_netns(target=target, from_netns=from_netns)

    def ping_from_netns(self, target, data_size=56, from_netns=None):
        """
        Ping a given destination from source.

        :parameter source: the host which executes the ping command
        :parameter password: the root password for the host source
        :parameter target: the target of the ping command
        :parameter data_size: the size of the data payload
        :parameter netns: optional networking namespace in which to execute
        """
        netns_prefix = f'ip netns exec {from_netns} ' if from_netns else ''
        version = ipaddress.ip_address(target).version
        cmd = netns_prefix + (f'ping -{version} -c 1 -M do -s {data_size} '
                              f'{target}')
        self.exec_command(cmd)

    def ping(self, target_ip, iface_name):
        """
        Ping an ip address via the specified interface
        :param target_ip: str
        :param iface_name: str
        """
        version = ipaddress.ip_address(target_ip).version
        self.exec_command(f'ping -{version} -c 1 -I {iface_name} {target_ip}')

    def get_global_ip(self, iface_name, ip_version):
        """
        :param str iface_name: interface name
        :param str ip_version: '4' or '6'
        :return: ipv4 or global ipv6 address as string
        """
        cmd = (f"ip -{ip_version} -o addr show {iface_name}"
               f" |awk '{{print $4}}' |cut -d '/' -f 1")
        if ip_version == '6':
            cmd += ' |grep -v fe80'
        return self.exec_command(cmd).decode('utf-8').strip()

    def lookup_ip_address_with_dns_query(self, hostname, ip_version):
        """
        Wait for the ip address to update in the dns lookup
        :param hostname: str
        :return: ipv4 address as a string
        """
        return syncutil.sync(
            exec_func=self._lookup_ip_address_with_dns_query,
            exec_func_args=(hostname, ip_version),
            success_criteria=lambda ip: ip != '',
            timeout=TIMEOUT
        )

    def _lookup_ip_address_with_dns_query(self, hostname, ip_version):
        """
        :param hostname: str
        :return: ipv4 address as a string
        """
        record_type = 'AAAA' if ip_version == '6' else 'A'
        cmd = f'dig +short {hostname} {record_type}'
        return self.exec_command(cmd).decode('utf-8').strip()

    def global_replace_str_in_file(self, old, new, filename):
        return self.exec_command(f'sed -i -r "s/{old}/{new}/g" "{filename}"')

    def restart_service(self, service_name):
        return self.exec_command(f'systemctl restart {service_name}')

    def __repr__(self):
        return (
            f'<Node| '
            f'address:{self._address}, '
            f'username:{self._username},'
            f'password:{self._password}>'
        )


class CirrosNode(Node):
    """
    A class to collect operations that need to be carried out via ssh
    on a Cirros machine
    """

    def assign_ip_with_dhcp_client(self, iface_name):
        """
        run dhcp client to assign an ip addresses for the specified interface
        :param str iface_name: interface name
        """
        self.exec_command(f'sudo /sbin/cirros-dhcpc up {iface_name}')
