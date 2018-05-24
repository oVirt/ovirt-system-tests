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
        if status != 0:
            stderr_message = stderr.read()
            raise SshException('Ssh command "{command}" exited with status '
                               'code {status}. Stderr: {stderr}'
                               .format(command=command, status=status,
                                       stderr=stderr_message))
        return stdout.read()
    finally:
        client.close()
