# Copyright 2014 Red Hat, Inc.
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

import click

import functools
import logging
import os
import time
from configparser import SafeConfigParser
import sys
from future.builtins import super

import nose.core
import nose.config
import nose.plugins
from nose.plugins.skip import SkipTest
from nose.plugins.xunit import Xunit
import unittest
import unittest.case
from signal import signal, SIGTERM, SIGHUP
import datetime

import log_utils

LOGGER = logging.getLogger(__name__)
LogTask = functools.partial(log_utils.LogTask, logger=LOGGER)
log_task = functools.partial(log_utils.log_task, logger=LOGGER)


def exit_handler(signum, frame):
    """
    Catch SIGTERM and SIGHUP and call "sys.exit" which raises
    "SystemExit" exception.
    This will trigger all the cleanup code defined in ContextManagers
    and "finally" statements.

    For more details about the arguments see "signal" documentation.

    Args:
        signum(int): The signal's number
        frame(frame): The current stack frame, can be None
    """
    LOGGER.debug('signal {} was caught'.format(signum))
    sys.exit(128 + signum)


@click.command()
@click.argument(
    'test',
    type=click.Path(exists=True),
    required=True,
    metavar='<test>',
)
@click.option(
    '-j', '--junitxml-path',
    required=True,
    help='Test results junitxml path.'
)
def cli(test, junitxml_path):
    signal(SIGTERM, exit_handler)
    signal(SIGHUP, exit_handler)

    logging.root.handlers = [
        log_utils.TaskHandler(
            level=logging.INFO,
            dump_level=logging.ERROR,
            formatter=log_utils.ColorFormatter(fmt='%(msg)s', )
        )
    ]

    logging.captureWarnings(True)
    if not run_test(click.format_filename(test), junitxml_path):
        LOGGER.error('Test {} failed'.format(test))
        sys.exit(1)


def _create_output_filename(
    default_dir, default_filename, output_filename=None
):
    """
    Given a default_dir, default_filename, output_filename(optional)
    returns the result_path
    Args:
        default_dir (str): Containing the default directory for keeping
        the log file
        default_filename (str): Containing the default filename for the
        log file
        output_filename (str): Containing the requested filename for
        the log file (can be a filename or a full/relative path)
    Returns:
        str: results_path represents the fullname of the output file
        ( dir + basename )
    """

    if output_filename:
        dirname, basename = os.path.split(output_filename)
        if dirname:
            default_dir = dirname
        if basename:
            default_filename = basename

    results_path = os.path.abspath(
        os.path.join(
            default_dir,
            default_filename,
        )
    )
    return results_path


def _safe_makedir(path):
    """
    Given a path recursivley create the directories and
    don't fail if already exists
    Args:
        path (str): Containing the path to be created
    Raises:
        OSError: if it fails to create the directory
        (if directory exists no exception will be raise)
    """
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != os.errno.EEXIST:
            raise

def run_test(path, junitxml_file=None):
    with LogTask('Run test: %s' % os.path.basename(path)):
        env = os.environ.copy()
        results_path = _create_output_filename(
            os.curdir,
            os.path.basename(path) + ".junit.xml", junitxml_file
        )
        _safe_makedir(os.path.dirname(results_path))
        noseargs = [
            '--with-xunit',
            '--xunit-file=%s' % results_path,
            '--with-tasklog-plugin',
             #   '--with-log-collector-plugin',
        ]

        class DummyStream(object):
            def write(self, *args):
                pass

            def writeln(self, *args):
                pass

            def flush(self):
                pass

        config = nose.config.Config(
            verbosity=3,
            env=env,
            plugins=nose.core.DefaultPluginManager(),
            stream=DummyStream(),
            stopOnError=True,
        )
        addplugins = [
            TaskLogNosePlugin(),
            #testlib.LogCollectorPlugin(self),
        ]

        result = nose.core.run(
            argv=['testrunner', path] + noseargs,
            config=config,
            addplugins=addplugins,
        )
        LOGGER.info('Results located at %s' % results_path)

        return result

class TaskLogNosePlugin(nose.plugins.Plugin):
    name = "tasklog-plugin"

    # the score parameter is a workaround to catch skipped tests
    # see: https://github.com/nose-devs/nose/issues/45
    score = 10000

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('nose')
        self.skipped = {}
        super(TaskLogNosePlugin, self).__init__(*args, **kwargs)

    def options(self, parser, env):
        return super(TaskLogNosePlugin, self).options(parser, env)

    def configure(self, options, conf):
        res = super(TaskLogNosePlugin, self).configure(options, conf)
        self.logger.handlers = logging.root.handlers
        return res

    def startTest(self, test):
        log_utils.start_log_task(
            test.shortDescription() or str(test), logger=self.logger
        )
    def stopTest(self, test):
        desc = test.shortDescription() or str(test)
        level = 'info'

        if desc in self.skipped:
            exp_msg = ''
            try:
                exp_msg = self.skipped[desc][1]
            except KeyError:
                pass
            self.logger.info('SKIPPED: %s', exp_msg)

        if any(test.exc_info()):
            level = 'error'

        log_utils.end_log_task(desc, logger=self.logger, level=level)

    def addError(self, test, err):
        desc = test.shortDescription() or str(test)
        if issubclass(err[0], unittest.case.SkipTest):
            self.skipped[desc] = err


if __name__ == "__main__":
    cli()
