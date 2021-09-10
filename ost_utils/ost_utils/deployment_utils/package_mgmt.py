#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging
import os.path
import re

import requests


LOGGER = logging.getLogger(__name__)
REPO_NAME = 'extra-src-'

DUMMY_REPO_FILE = '''"
[dummy]
name=dummy
gpgcheck=0
baseurl={}
"'''.replace(
    '\n', '\\n'
)

DUMMY_REPOMD_XML = '''"
<repomd>
    <data type=\\"primary\\">
        <location href=\\"repodata/primary.xml\\"/>
    </data>
</repomd>
"'''.replace(
    '\n', '\\n'
)

DUMMY_PRIMARY_XML = '"<metadata packages="0"/>"'

OVIRT_PACKAGES_PATTERNS = (
    re.compile('ovirt-ansible-collection-[0-9]'),
    re.compile('ovirt-engine-[0-9]'),
    re.compile('python3-ovirt-engine-sdk4-[0-9]'),
    re.compile('vdsm-[0-9]'),
)


def expand_jenkins_repos(custom_repos):
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

        expanded_repos.update(repo_list)

    return list(r for r in expanded_repos if 'ppc64le' not in r)


def add_custom_repos(ansible_vm, repo_urls):
    for i, repo_url in enumerate(repo_urls):
        _add_custom_repo(ansible_vm, f"{REPO_NAME}{i + 1}", repo_url)


def disable_all_repos(ansible_vm):
    ansible_vm.shell('dnf config-manager --disable \'*\' || :')


def add_dummy_repo(ansible_vm):
    # use "non-standard" /etc path to keep things together,
    # we copy the contents to HE VM later
    repo_dir = '/etc/yum.repos.d/ost-dummy-repo'
    repodata_path = f'{repo_dir}/repodata'
    ansible_vm.file(
        path=repodata_path, mode='0777', state='directory', recurse=True
    )
    ansible_vm.copy(
        content=DUMMY_PRIMARY_XML,
        dest=os.path.join(repodata_path, 'primary.xml'),
    )
    ansible_vm.copy(
        content=DUMMY_REPOMD_XML,
        dest=os.path.join(repodata_path, 'repomd.xml'),
    )
    ansible_vm.copy(
        content=DUMMY_REPO_FILE.format(repo_dir),
        dest='/etc/yum.repos.d/dummy.repo',
    )


def check_installed_packages(ansible_vms):
    used_repos = _used_custom_repo_names(ansible_vms)

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


def _used_custom_repo_names(ansible_vms):
    repo_names = []

    for repo_no in range(1, 100):
        repo_name = f'{REPO_NAME}{repo_no}'
        result = ansible_vms.shell(f'dnf repolist {repo_name}')
        if all(len(res['stdout'].strip()) == 0 for res in result.values()):
            break
        repo_names.append(repo_name)

    return repo_names


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
