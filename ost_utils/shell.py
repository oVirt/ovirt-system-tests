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
        return "Command failed with rc={}. Stdout:\n{}\nStderr:\n{}\n".format(self.code, self.out, self.err)


def shell(args, bytes_output=False, **kwargs):
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    out, err = process.communicate()

    if not bytes_output:
        out = out.decode("utf-8")
        err = err.decode("utf-8")

    if process.returncode:
        raise ShellError(process.returncode, out, err)

    return out
