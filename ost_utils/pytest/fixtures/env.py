#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import os

import pytest


@pytest.fixture(scope='session')
def root_dir():
    return os.environ.get('OST_REPO_ROOT')


@pytest.fixture(scope='session')
def suite():
    return os.environ.get('SUITE')


@pytest.fixture(scope='session')
def suite_dir(root_dir, suite):
    return os.path.join(root_dir, suite)


@pytest.fixture(scope='session')
def working_dir():
    return os.environ.get('OST_DEPLOYMENT')


@pytest.fixture(scope='session')
def ssh_key_file():
    return os.environ.get('OST_IMAGES_SSH_KEY')


@pytest.fixture(scope="session")
def ost_images_distro():
    return os.environ.get('OST_IMAGES_DISTRO')


@pytest.fixture(scope="session")
def ost_he_storage_domain_type():
    return os.environ.get('OST_HE_STORAGE_DOMAIN_TYPE', 'nfs')


@pytest.fixture(scope='session')
def master_storage_domain_type():
    return os.environ.get('OST_MASTER_SD_TYPE', 'nfs')
