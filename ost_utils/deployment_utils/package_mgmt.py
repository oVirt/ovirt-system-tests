#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import logging
import os
import re
import zipfile

from typing import Optional

import requests

LOGGER = logging.getLogger(__name__)
REPO_NAME = 'extra-src-'

OVIRT_PACKAGES_PATTERNS = (
    re.compile('ovirt-ansible-collection-[0-9]'),
    re.compile('ovirt-engine-[0-9]'),
    re.compile('python3-ovirt-engine-sdk4-[0-9]'),
    re.compile('vdsm-[0-9]'),
)

OST_TO_GITHUB_DISTRO_NAME = {'el8stream': 'el8', 'el9stream': 'el9', 'rhel8': 'el8'}


def expand_repos(custom_repos, working_dir, ost_images_distro):
    repo_urls = []
    for repo_url in custom_repos:
        if re.match(r"https://(www\.|api\.)?github.com/(repos/)?oVirt", repo_url):
            repo_urls.append(expand_github_repo(repo_url, working_dir, ost_images_distro))
        else:
            repo_urls.extend(expand_jenkins_repo(repo_url, ost_images_distro))
    return repo_urls


def expand_github_repo(repo_url, working_dir, ost_images_distro):
    """
    This function converts custom repo links pointing to GitHub pull requests
    into local directories containing the unpacked RPMs from the artifacts ZIP
    on GitHub. This local directory is then later copied to each VM using the
    _add_custom_repo function below.

    This function supports several URL patterns:

    https://github.com/oVirt/REPONAME/pull/PR_ID
    https://github.com/oVirt/REPONAME/commit/COMMIT_HASH
    https://github.com/oVirt/REPONAME/actions/runs/RUN_ID
    https://api.github.com/oVirt/repos/REPONAME/actions/runs/RUN_ID/artifacts

    All artifacts will be downloaded and RPMs will be converted to repositories
    """
    match = re.search(
        r"^https://(www\.|api\.)?github.com/(repos/)?oVirt/([^/]+)/"
        r"(pulls?/([0-9]+)|commit/([a-z0-9]+)|actions/runs/([0-9]+)(/artifacts)?)$",
        repo_url,
    )
    if not match:
        raise RuntimeError(f"Not a valid GitHub link {repo_url}")
    _, _, repo, _, pr, commit, workflow_run, _ = match.groups()
    if not workflow_run:
        if not commit:
            commit = _github_resolve_pr_to_commit(repo, pr)
        workflow_run = _github_resolve_commit_to_workflow_run(repo, commit)

    artifacts: list[_GitHubArtifact] = _github_list_artifacts(repo, workflow_run)
    for artifact in artifacts:
        if OST_TO_GITHUB_DISTRO_NAME[ost_images_distro] in artifact.name:
            target_path = os.path.join(working_dir, 'github_artifacts', f'{commit}-{artifact.name}')
            os.makedirs(target_path, exist_ok=True)
            # Download the artifact
            target_file = _github_download_artifact(artifact, target_path)
            # Unpack the artifact
            _github_unpack_artifact(target_file)
            if _github_has_rpm(target_path):
                # TODO check metada presence and change repo local path
                # _github_generate_repomd(target_path)
                # Add to repos list.
                return target_path
    if not artifacts:
        raise RuntimeError(f"GH pr/commit/run {repo_url} had no artifacts with RPM files.")
    raise RuntimeError(f"GH pr/commit/run {repo_url} didn't match any of the artifacts names to distro name.")


def _github_has_rpm(path: str) -> bool:
    """
    This function checks if the specified path contains any RPM files.
    """
    for root, subdirs, files in os.walk(path):
        for file in files:
            if file.endswith(".rpm"):
                return True
    return False


class _GitHubArtifact:
    """
    This class contains the simplified data structure of an artifact in
    a response from the GitHub API. It only exists for typing purposes.
    """

    id: int
    name: str
    archive_download_url: str
    expired: bool

    def __init__(self, data: dict):
        self.id = int(data["id"])
        self.name = data["name"]
        self.archive_download_url = data["archive_download_url"]
        self.expired = bool(data["expired"])


class _GitHubArtifactResponse:
    """
    This class represents a simplified response with an artifact list from
    the GitHub API. It only exists for typing purposes.
    """

    artifacts: list[_GitHubArtifact]

    def __init__(self, data: dict):
        self.artifacts = [_GitHubArtifact(entry) for entry in data["artifacts"]]


def _github_resolve_pr_to_commit(repo: str, pr: str) -> str:
    """
    This function uses the GitHub API to look up the last commit on a specific
    PR and return the commit ID. This will then be used to look up the last
    run on that commit.
    """
    pulls_response = _github_get(f"https://api.github.com/repos/oVirt/{repo}/pulls/{pr}/commits")
    pulls: list[dict] = pulls_response.json()
    commit = pulls[-1]
    return commit["sha"]


def _github_resolve_commit_to_workflow_run(repo, commit) -> str:
    """
    This function uses the GitHub API to look up the last run for a commit.
    This run ID can then be used to obtain the artifacts.
    """

    # This is currently the only way to match workflow runs to commits -
    # listing all the workflow runs and filtering by commit sha. It's ugly
    # and we're checking only the last 100 runs. If it turns out it's not
    # enough we'll need to fetch multiple pages.
    runs_response = _github_get(
        f"https://api.github.com/repos/oVirt/{repo}/actions/runs",
        {"per_page": 100},
    )
    for run in runs_response.json()["workflow_runs"]:
        if run["head_sha"] == commit:
            run_id = run["id"]
            artifacts_response = _github_get(
                f"https://api.github.com/repos/oVirt/{repo}/actions/runs/{run_id}/artifacts"
            ).json()
            for artifact in artifacts_response["artifacts"]:
                if not artifact["expired"] and artifact["name"].startswith("rpm"):
                    return run_id

    raise RuntimeError(f"No workflow runs found for commit {commit}")


def _github_get(url: str, params: Optional[dict] = None) -> requests.Response:
    headers = {}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token is None:
        raise RuntimeError("GITHUB_TOKEN env variable is not defined - artifact retrieval " "won't be possible")
    headers["authorization"] = f"token {github_token}"
    if params is None:
        params = {}
    response = requests.get(url, headers=headers, allow_redirects=True, params=params)
    response.raise_for_status()
    return response


def _github_list_artifacts(repo: str, workflow_run: str) -> list[_GitHubArtifact]:
    """
    This function lists all artifacts for a specific GitHub Actions run.
    The returned list contains the GitHub API data struct
    """
    artifacts_response = _github_get(
        f"https://api.github.com/repos/oVirt/{repo}/" f"actions/runs/{workflow_run}/artifacts"
    )
    artifacts: _GitHubArtifactResponse
    artifacts = _GitHubArtifactResponse(artifacts_response.json())
    for artifact in artifacts.artifacts:
        if artifact.expired:
            raise RuntimeError(
                f"Artifact {artifact.name} for run {workflow_run} in repo" f" oVirt/{repo} has expired."
            )
    return artifacts.artifacts


def _github_download_artifact(artifact: _GitHubArtifact, target_dir: str) -> str:
    """
    This function downloads an artifact into the specified target directory
    with its original name.
    """
    target_file_path = os.path.join(target_dir, artifact.name)
    response = _github_get(artifact.archive_download_url)
    with open(target_file_path, "wb") as target_file:
        target_file.write(response.content)
    return target_file_path


def _github_unpack_artifact(path: str):
    """
    This function extracts a ZIP file specified in the path into its directory
    and then removes the ZIP file.
    """
    with zipfile.ZipFile(path, 'r') as zip_handle:
        zip_handle.extractall(os.path.dirname(path))
    os.unlink(path)


def expand_jenkins_repo(repo_url, ost_images_distro):
    expanded_repos = set()
    if requests.get(repo_url + '/repodata/repomd.xml').ok:
        return [repo_url]

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

    expanded_repos.update(repo for repo in repo_list if ost_images_distro in repo)

    return list(r for r in expanded_repos if 'ppc64le' not in r)


def add_custom_repos(ansible_vm, repo_urls):
    for i, repo_url in enumerate(repo_urls):
        _add_custom_repo(ansible_vm, f"{REPO_NAME}{i + 1}", repo_url)


def disable_all_repos(ansible_vm):
    # dnf is grumpy when it has no repos to work with, keep "dummy" enabled
    ansible_vm.shell('dnf config-manager --disable \'*\';' 'dnf config-manager --enable dummy;' ':')


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
    if url.startswith("/"):
        ansible_vm.copy(src=os.path.join(url, ''), dest=f"/etc/yum.repos.d/{name}")
        url = f"/etc/yum.repos.d/{name}"
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
    filtered_results = [line for res in results.values() for line in _filter_results(res['stdout'].splitlines())]

    LOGGER.debug(f'Packages used: {filtered_results}')

    return len(filtered_results) > 0


def _filter_results(result):
    try:
        indx = result.index('Installed Packages')
    except ValueError:
        return []
    return result[indx + 1 :]
