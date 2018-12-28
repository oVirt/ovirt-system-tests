# ovirtlib
# Copyright (C) 2019 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

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
