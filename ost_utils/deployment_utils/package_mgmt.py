#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging
import os
import re

import requests


LOGGER = logging.getLogger(__name__)
REPO_NAME = 'extra-src-'

OVIRT_PACKAGES_PATTERNS = (
    re.compile('ovirt-ansible-collection-[0-9]'),
    re.compile('ovirt-engine-[0-9]'),
    re.compile('python3-ovirt-engine-sdk4-[0-9]'),
    re.compile('vdsm-[0-9]'),
)


def expand_jenkins_repos(custom_repos, ost_images_distro):
    expanded_repos = set()
    for repo_url in custom_repos:
        if requests.get(repo_url + '/repodata/repomd.xml').ok:
            expanded_repos.add(repo_url)
            continue

        lvl1_page = requests.get(repo_url + '/api/json?depth=3')
        lvl1_page.raise_for_status()
        lvl1_page = lvl1_page.json()

        url = lvl1_page['url']
        if url.endswith('/'):
            url = url[:-1]

        repo_list = set()
        for artifact in lvl1_page.get('artifacts', []):
            if not artifact['relativePath'].endswith('rpm'):
                continue
            relative_path = artifact['relativePath'].split('/')[0]
            new_url = f'{url}/artifact/{relative_path}'
            repo_list.add(new_url)

        if len(repo_list) == 0:
            raise RuntimeError(f"Couldn't find any repos at {repo_url}")

        expanded_repos.update(
            repo for repo in repo_list if ost_images_distro in repo
        )

    return list(r for r in expanded_repos if 'ppc64le' not in r)


def add_custom_repos(ansible_vm, repo_urls):
    for i, repo_url in enumerate(repo_urls):
        _add_custom_repo(ansible_vm, f"{REPO_NAME}{i + 1}", repo_url)


def disable_all_repos(ansible_vm):
    # dnf is grumpy when it has no repos to work with, keep "dummy" enabled
    ansible_vm.shell(
        'dnf config-manager --disable \'*\';'
        'dnf config-manager --enable dummy;'
        ':'
    )


def check_installed_packages(ansible_vms):
    used_repos = {
        os.path.basename(file['path']).removesuffix('.repo')
        for host in ansible_vms.find(
            paths='/etc/yum.repos.d',
            patterns=f'{REPO_NAME}.*',
            use_regex=True,
        ).values()
        for file in host['files']
    }

    if len(used_repos) == 0:
        return

    for repo in used_repos:
        if _are_any_packages_used(ansible_vms, repo):
            return

    raise RuntimeError(
        'None of user custom repos has been used. '
        'Your packages are too old. If you are trying to test '
        'your patch, please rebase on top of latest master '
        'branch!'
    )


def report_ovirt_packages_versions(ansible_vms):
    pkgs = set()

    for res in ansible_vms.shell('rpm -qa').values():
        pkgs.update(res['stdout'].splitlines())

    matching_pkgs = filter(
        lambda pkg: any(pat.match(pkg) for pat in OVIRT_PACKAGES_PATTERNS),
        pkgs,
    )

    LOGGER.info('oVirt packages used on VMs:')
    for pkg in sorted(matching_pkgs):
        LOGGER.info(pkg)


def _add_custom_repo(ansible_vm, name, url):
    LOGGER.info(f"Adding repository to VM: {name} -> {url}")
    ansible_vm.yum_repository(
        name=name,
        description=name,
        baseurl=url,
        gpgcheck=False,
        sslverify=False,
    )
    # 'module_hotfixes' option is not available with 'yum_repository' module
    ansible_vm.ini_file(
        path=f"/etc/yum.repos.d/{name}.repo",
        section=name,
        option="module_hotfixes",
        value=1,
    )


def _are_any_packages_used(ansible_vms, repo_name):
    results = ansible_vms.shell(f'dnf repo-pkgs {repo_name} list installed')
    filtered_results = [
        line
        for res in results.values()
        for line in _filter_results(res['stdout'].splitlines())
    ]

    LOGGER.debug(f'Packages used: {filtered_results}')

    return len(filtered_results) > 0


def _filter_results(result):
    try:
        indx = result.index('Installed Packages')
    except ValueError:
        return []
    return result[indx + 1 :]
