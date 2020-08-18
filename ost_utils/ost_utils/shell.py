#
# Copyright 2020 Red Hat, Inc.
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

from __future__ import absolute_import

import subprocess


class ShellError(Exception):

    def __init__(self, code, out, err):
        self.code = code
        self.out = out
        self.err = err

    def __str__(self):
        return "Command failed with rc={}. Stdout:\n{}\nStderr:\n{}\n".format(
            self.code, self.out, self.err
        )


def shell(args, bytes_output=False, **kwargs):
    process = subprocess.Popen(args,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               **kwargs)
    out, err = process.communicate()

    if not bytes_output:
        out = out.decode("utf-8")
        err = err.decode("utf-8")

    if process.returncode:
        raise ShellError(process.returncode, out, err)

    return out
