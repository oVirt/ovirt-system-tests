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

from ost_utils import backend


def all():
    return "*"


def engine():
    return backend.default_backend().engine_hostname()


def host0():
    return backend.default_backend().hosts_hostnames()[0]


def host1():
    return backend.default_backend().hosts_hostnames()[1]


# https://docs.ansible.com/ansible/latest/user_guide/intro_patterns.html#using-regexes-in-patterns
def hosts():
    return "~({})".format(
        "|".join(backend.default_backend().hosts_hostnames())
    )


def storage():
    return backend.default_backend().storage_hostname()
