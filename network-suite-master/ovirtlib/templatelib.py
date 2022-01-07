#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
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
        success_criteria=_check_template,
    )


def _get_template(templates_service, template_name):
    try:
        return next(template for template in templates_service.list() if template.name == template_name)
    except StopIteration:
        return None


def _check_template(template):
    return template.status == TemplateStatus.OK if template else False
