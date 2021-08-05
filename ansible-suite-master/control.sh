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
    env_status
    cd "$OST_REPO_ROOT"
    declare failed=false

    "${PYTHON}" -m tox -e deps
    source "${OST_REPO_ROOT}/.tox/deps/bin/activate"

    env_run_pytest_bulk "${SUITE}/test-scenarios" || failed=true

    if $failed; then
        echo "@@@@ ERROR: Failed running ${SUITE}"
        return 1
    fi
}
