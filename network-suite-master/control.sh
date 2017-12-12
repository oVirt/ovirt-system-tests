#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

install_dependencies() {
    yum install -y python-pip
    pip install -U pip
    pip install flake8==3.1.0
    pip install pytest
}

run_static_analysis() {
    flake8 --statistics --show-source "${SUITE}"
}

create_env() {
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
    python -m pytest -s -v --durations=0 --lago-env "$PREFIX" "${SUITE}/tests"
}

run_suite () {
    install_dependencies
    run_static_analysis
    create_env
    run_tests
}
