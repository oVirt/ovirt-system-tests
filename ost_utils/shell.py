#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import subprocess


class ShellError(Exception):
    def __init__(self, code, out, err):
        self.code = code
        self.out = out
        self.err = err

    def __str__(self):
        return f"Command failed with rc={self.code}. Stdout:\n{self.out}\nStderr:\n{self.err}\n"


def shell(args, bytes_output=False, **kwargs):
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs) as process:
        out, err = process.communicate()

        if not bytes_output:
            out = out.decode("utf-8")
            err = err.decode("utf-8")

        if process.returncode:
            raise ShellError(process.returncode, out, err)

        return out
