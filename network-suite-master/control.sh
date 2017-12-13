#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

install_dependencies() {
    yum install -y python-pip
    pip install -U pip
    pip install flake8==3.1.0
    pip install pylint==1.6.4
    pip install pytest
}

run_static_analysis() {
    flake8 --statistics --show-source "${SUITE}"
    pylint --rcfile="${SUITE}/pylintrc" --errors-only "${SUITE}/lib" "${SUITE}/tests"
}

setup_env() {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    install_local_rpms
}

start_env() {
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
    setup_env
    run_static_analysis
    start_env
    run_tests
}
