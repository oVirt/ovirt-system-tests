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
    declare failed=false

    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    "${PYTHON}" -m pip install --user "pytest==6.2.2"

    env_run_pytest_bulk "${SUITE}/test-scenarios" || failed=true

    if [[ -z "$OST_SKIP_COLLECT" || "${failed}" == "true" ]]; then
        env_collect "$PWD/test_logs/${SUITE_NAME}"
    fi

    if $failed; then
        echo "@@@@ ERROR: Failed running ${SUITE_NAME}"
        return 1
    fi
}
