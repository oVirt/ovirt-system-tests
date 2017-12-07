#!/bin/env python

import os
from re import compile
from subprocess import check_output
from operator import or_
from itertools import imap
import logging

from change_resolver_conf import CONF

logging.basicConfig(filename='change_resolver.log', level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


def main():
    changes = get_changes()
    change_to_suite = ChangeResolver()
    change_set = reduce(or_, imap(change_to_suite, changes))
    if not change_set:
        LOGGER.info('Changes were not detected, returning default suites')
        change_set = CONF['default_suites']
    exclude_set = CONF['exclude']
    LOGGER.debug('excluding: {}'.format(','.join(change_set & exclude_set)))
    print '\n'.join(change_set - exclude_set)


def get_changes():
    return (
        l for l in check_output(
            ["git", "show", "--pretty=format:", "--name-only"]
        ).splitlines()
        if l
    )


class ChangeResolver:
    def __call__(self, change):
        return self.resolve_change(change)

    @property
    def _core_files_rgx(self):
        if not hasattr(self, '_core_files_rgx_cache'):
            self._core_files_rgx_cache = \
                compile(
                    '(check-patch.sh|run_suite.sh|suite.sh|change_resolver.py)'
                )
        return self._core_files_rgx_cache

    @property
    def _suite_files_rgx(self):
        if not hasattr(self, '_suite_files_rgx_cache'):
            self._suite_files_rgx_cache = compile(
                "(?P<suite_type>[^\/]*(-|_)suite(-|_)" +
                "(?P<suite_version>[0-9]+\.[0-9]+|master))"
            )
        return self._suite_files_rgx_cache

    def resolve_change(self, change):
        suites_to_run = set()
        LOGGER.info('resolving change: {}'.format(change))
        core_files_changed = self._core_files_rgx.search(change)
        if core_files_changed:
            LOGGER.info(
                'OST core file changed. Adding {}'.format(
                    ','.join(CONF['core_suites'])
                )
            )
            return CONF['core_suites']

        suite_files_changed = self._suite_files_rgx.search(change)
        if suite_files_changed:
            suites_to_run = set(
                [suite_files_changed.group('suite_type')]
            )

        related_symlinks = self.resolve_symlinks(change)
        if related_symlinks:
            LOGGER.info('found related symlinks: {}'.format(related_symlinks))
            suites_to_run = or_(related_symlinks, suites_to_run)

        LOGGER.debug(
            'for change: {} -> related suites: {}'
            .format(change, suites_to_run)
        )
        return suites_to_run

    def realpath_wrapper(self, path):
        real_path = os.path.realpath(path)
        LOGGER.info(
            'resolving realpath for symlink: {} -> {}'
            .format(path, real_path)
        )
        if os.path.islink(real_path):
            raise RuntimeError(
                'You have a loop of symlinks at {}'
                .format(real_path)
            )
        return real_path

    def path_to_suite(self, path):
        suite = self._suite_files_rgx.search(path)
        if suite:
            return suite.group('suite_type')

    def resolve_symlinks(self, change):
        if not hasattr(self, '_suites'):
            self.make_symlinks_cache()
        return self._suites.get(os.path.join(os.getcwd(), change))

    def make_symlinks_cache(self):
        paths = (
            os.path.join(path, f)
            for path, _, files in os.walk(os.path.curdir)
            for f in files
        )
        paths_iterator = (
            (f, self.realpath_wrapper(f)) for f in paths if os.path.islink(f)
        )
        self._suites = dict()
        for symlink, f in paths_iterator:
            self._suites.setdefault(f, set()).add(self.path_to_suite(symlink))
        LOGGER.debug('generated file to suite(s) map:\n{}'.format(self._suites))
        return self._suites


if __name__ == "__main__":
    main()
