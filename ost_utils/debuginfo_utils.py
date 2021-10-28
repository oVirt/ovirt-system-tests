#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import pprint
import re


_generic_object_re = re.compile(r'^<\S* object at 0x[0-9A-Fa-f]*>')


def obj_info(obj):
    """
    Get an object, return a string that includes information about it.
    If "str(obj)" does not match "<$class object at $address>", use that.
    Otherwise, report all "interesting and harmless" attribute values.
    """
    res = str(obj)
    if not _generic_object_re.match(res):
        return pprint.pformat(obj)
    values = {}
    for attr in dir(obj):
        if (
            # Private?
            not attr.startswith('_')
            # Do not run properties' code here
            and not (
                hasattr(type(obj), attr)
                and isinstance(getattr(type(obj), attr), property)
            )
            and hasattr(obj, attr)
            # Let's agree that 'None' is not interesting
            and getattr(obj, attr) is not None
        ):
            # TODO: Consider recursing?
            # values[attr] = obj_info(getattr(obj, attr))
            # If we do, need to prevent endless recursion, perhaps limit depth
            values[attr] = getattr(obj, attr)
    return f'{res}:\n{pprint.pformat(values)}'
