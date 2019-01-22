#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from os import path
from setuptools import setup, find_packages


with open(path.join(path.dirname(__file__), 'requirements.txt')) as f:
    requirements = f.read()

setup(
    author="oVirt System Tests maintainers",
    author_email='ovirt@infra@ovirt.org',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
    description="Utilities for running oVirt System Tests",
    install_requires=requirements,
    license="Apache Software License 2.0",
    include_package_data=True,
    keywords='OST',
    name='ost_utils',
    packages=find_packages(),
    url='https://gerrit.ovirt.org/ovirt-system-tests',
    version='0.1.0',
    zip_safe=False,
)
