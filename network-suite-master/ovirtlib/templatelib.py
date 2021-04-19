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
from ovirtsdk4 import types

from ovirtlib import syncutil
from ovirtlib.sdkentity import EntityNotFoundError


TEMPLATE_BLANK = 'Blank'


class TemplateStatus(object):

    OK = types.TemplateStatus.OK
    ILLEGAL = types.TemplateStatus.ILLEGAL
    LOCKED = types.TemplateStatus.LOCKED


def get_template(system, template_name):
    template = _get_template(system.templates_service, template_name)
    if template is None:
        raise EntityNotFoundError
    return template


def wait_for_template_ok_status(system, template_name):
    syncutil.sync(
        exec_func=_get_template,
        exec_func_args=(system.templates_service, template_name),
        success_criteria=_check_template
    )


def _get_template(templates_service, template_name):
    try:
        return next(template for template in templates_service.list()
                    if template.name == template_name)
    except StopIteration:
        return None


def _check_template(template):
    return template.status == TemplateStatus.OK if template else False
