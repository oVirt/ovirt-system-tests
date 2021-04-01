#!/usr/bin/env python
#
from __future__ import print_function, absolute_import
import os
import yaml
from prettytable import PrettyTable
from itertools import chain
import click
from warnings import warn
from jinja2.exceptions import TemplateError

from render_jinja_templates import render


REUIREMENT_FIELDS = ('memory',)
TABLE_FIELDS = tuple(
    ['Suite', 'Domain'] + [f.capitalize() for f in REUIREMENT_FIELDS]
)
INIT_FILE_IN_NAME = 'LagoInitFile.in'
INIT_FILE_NAME = 'LagoInitFile'


@click.command()
@click.argument('suite_paths', nargs=-1, type=click.Path(
    exists=True, file_okay=False, dir_okay=True
))
@click.option('--border/--no-border', default=True)
@click.option('--header/--no-header', default=True)
@click.option('--totals-only', is_flag=True)
@click.option('--sortby', type=click.Choice(TABLE_FIELDS))
@click.option('--fields', type=click.Choice(TABLE_FIELDS), multiple=True)
def print_suite_reuirements(suite_paths, totals_only, **kwargs):
    pt = PrettyTable(TABLE_FIELDS)
    pt.align = 'r'
    pt.align['Suite'] = 'l'
    pt.align['Domain'] = 'l'
    for suite_path in suite_paths:
        if suite_path.endswith('/'):
            suite_path = suite_path[:-1]
        rows = get_suite_rows(suite_path, totals_only)
        for row in rows:
            pt.add_row([os.path.basename(suite_path)] + row)
    print(pt.get_string(**kwargs))


def get_suite_rows(suite_path, totals_only):
    sr = get_suite_reuirements(suite_path)
    if sr is None:
        return []
    totals = [['Totals'] + list(sr['totals'].values())]
    if totals_only:
        return totals
    rows = chain(
        (
            [dn] + list(dr.values()) for dn, dr in
            sr['requirements'].items()
        ),
        totals,
    )
    return rows


def get_suite_reuirements(suite_path):
    init_data = get_suite_init_data(suite_path)
    if init_data is None:
        warn('Can`t read init file at {}, can`t calculate requirements'.format(
            suite_path
        ))
        return
    requirements = {
        dname: get_domain_requirements(ddata)
        for dname, ddata in init_data.get('domains', {}).items()
    }
    totals = {
        field: sum(dr[field] for dr in requirements.values())
        for field in REUIREMENT_FIELDS
    }
    return dict(requirements=requirements, totals=totals)


def get_suite_init_data(suite_path):
    try:
        init_file_in = os.path.join(suite_path, INIT_FILE_IN_NAME)
        os.environ['suite_name'] = os.path.basename(suite_path)
        return yaml.safe_load(render(init_file_in))
    except IOError as e:
        if e.errno == 2:
            # ignore if file not found (will try non-template file)
            pass
    except TemplateError:
        # If we can't render the template, treat as empty file
        return None
    try:
        with open(os.path.join(suite_path, INIT_FILE_NAME)) as f:
            return yaml.safe_load(f)
    except IOError as e:
        if e.errno == 2:
            # Return None if file not found
            return None


def get_domain_requirements(domain_data):
    return {
        'memory': domain_data.get('memory', 0)
    }


if __name__ == '__main__':
    print_suite_reuirements()
