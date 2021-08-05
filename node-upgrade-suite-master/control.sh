#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

run_suite () {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_start
    env_dump_ansible_hosts
    env_wait_for_ssh
    env_add_extra_repos
    env_status
    cd "$OST_REPO_ROOT"
    if ! env_deploy; then
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi
    declare test_scenarios="${SUITE}/test-scenarios"
    declare failed=false

    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    "${PYTHON}" -m pip install --user -I selenium || echo "ERROR: pip failed, webdriver will fail to connect"
    "${PYTHON}" -m pip install --user "pytest==6.2.2"

    env_run_pytest_bulk ${test_scenarios[@]} || failed=true

    if $failed; then
        echo "@@@@ ERROR: Failed running ${SUITE}"
        return 1
    fi
}
