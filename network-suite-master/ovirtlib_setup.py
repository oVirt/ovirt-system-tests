#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# ovirtlib

from distutils.core import setup

from ovirtlib import version

setup(
    author="Edward Haas, Leon Goldberg",
    author_email="edwardh@redhat.com, lgoldber@redhat.com",
    description="oVirt SDK python lib",
    license="GNU GPLv2+",
    name="ovirtlib",
    packages=["ovirtlib"],
    platforms=["Linux"],
    url="https://gerrit.ovirt.org/gitweb?p=ovirt-system-tests.git;a=tree",
    version=version.VERSION,
)
