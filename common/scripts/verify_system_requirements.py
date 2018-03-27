#!/bin/python

"""
Verify that the host requirements for a given suite.
The requirements should be placed inside the suite's "/vars/main.yml" file,
under the "host_requirements" key.
"""

import argparse
from copy import deepcopy
import errno
import logging
import os
from collections import namedtuple
from functools import partial, update_wrapper
from sys import argv, exit
import yaml

DiskUsage = namedtuple('DiskUsage', ['total', 'used', 'free'])
GB = 1024 ** 3

logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

DEFAULTS = {
    'disk_space_gb': 15
}

class RequirementIsNotSatisfiedException(Exception):
    pass

def _partial(f, *args, **kwargs):
    partial_f = partial(f, *args, **kwargs)
    update_wrapper(partial_f, f)

    return partial_f

def disk_usage(path):
    """
    Return disk usage statistics about the given path.
    Returned value is a named tuple with attributes 'total', 'used' and
    'free', which are the amount of total, used and free space, in bytes.
    """
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize

    return DiskUsage(total=total, used=used, free=free)

def load_requirements(config_path):
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
        # The file doesn't exist, use defaults
        LOGGER.warning('{} does not exist'.format(config_path))
        requirements = {}
    else:
        requirements = config.get('system_requirements', {})

    if not requirements:
        LOGGER.info('Requirements dict is empty, using default requirements')

    config = deepcopy(DEFAULTS)
    config.update(requirements)

    return config

def disk_space(requirements, prefix_path):
    """
    Verify that there is enough disk space to run the suite
    """
    required_space = int(requirements['disk_space_gb']) * GB
    free_space = disk_usage(prefix_path).free

    if required_space > free_space:
        raise RequirementIsNotSatisfiedException(
            '{}, Required space: {}, Free space: {}'.format(
                prefix_path,
                required_space,
                free_space
            )
        )

def main():
    parser = argparse.ArgumentParser(description=globals()['__doc__'])
    parser.add_argument('config_path', help="Path to the suite's config")
    parser.add_argument(
        '--prefix-path',
        default=os.curdir,
        type=str,
        help='The dir in which the Lago environment will be created'
    )

    args = parser.parse_args(argv[1:])
    requirements = load_requirements(args.config_path)
    failed = False

    checks = [
        _partial(disk_space, requirements, args.prefix_path),
    ]

    for check in checks:
        try:
            check()
            LOGGER.info('{} success'.format(check.__name__))
        except RequirementIsNotSatisfiedException as e:
            LOGGER.error('{} requirements are not satisfied.\n{}'.format(
                check.__name__, e.message)
            )
            failed = True

    if failed:
        LOGGER.error('Some checks failed')
        exit(1)

    LOGGER.info('All checks passed')

if __name__ == "__main__":
    main()
