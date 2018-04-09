"""
This module contains the configuration of change_resolver.py

The configuration should be placed in a dict called CONF inside this module.
This module should be placed in the same dir with 'change_resolver.py'.

About the configuration options:

    - default_suites: suites to run if the change resolver returns an
      empty set.
    - core_suites: suites to run if a core file has been changed.
    - exclude: suites that will be excluded from the change list.
"""

CONF = {
    'default_suites': {
        'basic-suite-master',
    },
    'core_suites': {
        'basic-suite-master',
    },
    'exclude': set()
}
