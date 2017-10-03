#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

create_env() {
    yum install python-pip
    pip install pytest

    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    install_local_rpms
    env_start
    env_status
    if ! env_deploy; then
        env_collect "$PWD/test_logs/${SUITE##*/}/post-000_deploy"
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi
}

run_tests() {
    python -m pytest -s -v --lago-env "$PREFIX" "${SUITE}/tests"
}

run_suite () {
    create_env
    run_tests
}
