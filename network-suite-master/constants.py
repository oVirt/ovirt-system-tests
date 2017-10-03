# -*- coding: utf-8 -*-
#
# Copyright 2017 Red Hat, Inc.
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
class Lago(object):

    SUITE_NAME = 'network-suite-master'
    ENGINE_DOMAIN = '-'.join(('lago', SUITE_NAME, 'engine'))
    HOST_0_DOMAIN = '-'.join(('lago', SUITE_NAME, 'host-0'))
    HOST_1_DOMAIN = '-'.join(('lago', SUITE_NAME, 'host-1'))


class Size(object):

    MB = 2 ** 20
    GB = 2 ** 30


class Storage(object):

    SD_GLANCE_NAME = 'ovirt-image-repository'
    SD_NFS_NAME = 'nfs'
    SD_NFS_PATH = '/exports/nfs/share1'

    CIRROS_IMAGE_NAME = 'CirrOS 0.3.5 for x86_64'
    GLANCE_DISK_NAME = (CIRROS_IMAGE_NAME.replace(" ", "_") +
                        '_glance_disk')
    TEMPLATE_CIRROS = (CIRROS_IMAGE_NAME.replace(" ", "_") +
                       '_glance_template')

    TEMPLATE_BLANK = 'Blank'


class Network(object):

    OVIRTMGMT = 'ovirtmgmt'


class DataCenter(object):

    NAME = 'Default'


class Cluster(object):

    NAME = 'Default'
