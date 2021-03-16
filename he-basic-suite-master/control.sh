#!/bin/bash -xe
set -o pipefail

prep_suite () {
    render_jinja_templates
}

setup_ipv6() {
    export IPV6_ONLY=True
    export IPV6_SUBNET=$(python "${OST_REPO_ROOT}/he-basic-ipv6-suite-master/find_ipv6_subnet.py" \
    "$PREFIX" "lago-${SUITE##*/}-net-mgmt-ipv6")
}

run_suite(){
    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    "${PYTHON}" -m pip install --user \
        "importlib_metadata==2.0.0" \
        "pytest==6.2.2" \
        "zipp==1.2.0"

    local suite="${SUITE?}"
    local curdir="${PWD?}"
    declare failed=false
    env_init \
        "$1" \
        "$suite/LagoInitFile"
    env_repo_setup
    if [[ -e "${SUITE}/reposync-config-sdk4.repo" ]]; then
        install_local_rpms_without_reposync
    else
        cd $PREFIX
        lago ovirt reposetup \
            --reposync-yum-config ${suite}/reposync-he.repo
        cd -
        install_local_rpms
    fi
    env_start
    env_dump_ansible_hosts
    env_copy_repo_file
    env_copy_config_file
    cd "$OST_REPO_ROOT"

    if [[ ${suite} == *"ipv6"* ]]; then
        setup_ipv6
    fi

    env_deploy

    declare test_scenarios="${SUITE}/test-scenarios"

    env_run_pytest_bulk ${test_scenarios[@]} || failed=true
    env_collect "$curdir/test_logs/${suite##*/}"
    if $failed; then
        echo "@@@@ ERROR: Failed running ${suite}"
        return 1
    fi
}
