#!/bin/bash -xe
set -o pipefail

prep_suite () {
    render_jinja_templates
}

run_suite () {
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    declare failed=false
    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_start
    env_status
    cd "$OST_REPO_ROOT"

    "${PYTHON}" -m tox -e deps
    source "${OST_REPO_ROOT}/.tox/deps/bin/activate"

    declare test_scenarios="${SUITE}/test-scenarios"
    declare failed=false

    env_run_pytest_bulk "$test_scenarios" || failed=true

    if $failed; then
        echo "@@@@ ERROR: Failed running ${suite}"
        return 1
    fi
}
