#!/bin/bash -xe
set -o pipefail

prep_suite () {
    render_jinja_templates
}

run_suite(){
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    declare failed=false
    env_init \
        "$1" \
        "$suite/LagoInitFile"
    env_start
    cd "$OST_REPO_ROOT"

    declare test_scenarios="${SUITE}/test-scenarios"

    "${PYTHON}" -m tox -e deps
    source "${OST_REPO_ROOT}/.tox/deps/bin/activate"

    env_run_pytest_bulk "$test_scenarios" || failed=true
    if $failed; then
        echo "@@@@ ERROR: Failed running ${suite}"
        return 1
    fi
}
