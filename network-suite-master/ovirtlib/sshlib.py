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
import paramiko


DEFAULT_USER = 'root'


class SshException(Exception):
    pass


def exec_command(address, password, command, username=DEFAULT_USER):
    """
    Execute a ssh command on a host
    :param address: address of the endpoint
    :param password: the password
    :param command: command to be executed
    :param username: the username, root if not specified
    :returns stdout: the standard output of the command
    :raises exc: Exception: if the command returns a non-zero exit status
    Example:
    hostname = sshlib.exec_command('192.168.1.5', 'password', 'hostname')
    """

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(address, username=username, password=password)
    try:
        _, stdout, stderr = client.exec_command(command)
        status = stdout.channel.recv_exit_status()
        stdout_message = stdout.read()
        if status != 0:
            stderr_message = stderr.read()
            raise SshException(
                f'Ssh command "{command}" exited with status code {status}. '
                f'Stderr: {stderr_message}. Stdout: {stdout_message}. '
            )
        return stdout_message
    finally:
        client.close()


class Node(object):
    """
    A class to collect operations that need to be carried out on a node (host
    or VM) but are not supported by the corresponding oVirt objects.
    """

    def __init__(self, address, password, username=DEFAULT_USER):
        self._address = address
        self._username = username
        self._password = password

    def exec_command(self, command):
        return exec_command(
            address=self._address,
            password=self._password,
            command=command,
            username=self._username
        )

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
