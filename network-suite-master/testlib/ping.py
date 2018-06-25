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

from lib import sshlib
from lib.sshlib import SshException


class PingFailed(SshException):
    pass


def ssh_ping(source, password, destination):
    """
    Ping a given destination from source.

    :parameter source: the host which executes the ping command
    :parameter password: the root password for the host source
    :parameter destination: the destination of the ping command
    """

    cmd = 'ping -4 -c 1 ' + destination
    try:
        sshlib.exec_command(source, password, cmd)
    except SshException as err:
        raise PingFailed(err)
