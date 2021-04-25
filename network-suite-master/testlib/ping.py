#
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
#

from ovirtlib import sshlib
from ovirtlib.sshlib import SshException


class PingFailed(SshException):
    pass


def ssh_ping(source, password, destination, data_size=56, netns=None):
    """
    Ping a given destination from source.

    :parameter source: the host which executes the ping command
    :parameter password: the root password for the host source
    :parameter destination: the destination of the ping command
    :parameter data_size: the size of the data payload
    :parameter netns: optional networking namespace in which to execute
    """
    netns_prefix = 'ip netns exec {} '.format(netns) if netns else ''
    cmd = netns_prefix + 'ping -4 -c 1 -M do -s {} {}'.format(
        data_size, destination)
    try:
        sshlib.Node(source, password).exec_command(cmd)
    except SshException as err:
        raise PingFailed(err)
