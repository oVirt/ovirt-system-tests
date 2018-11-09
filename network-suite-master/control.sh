#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

install_dependencies() {
    yum install -y python-pip
    pip install -U pip==9.0.3
    pip install flake8==3.1.0
    pip install pylint==1.6.4
    pip install pytest==3.5

    pip install contextlib2

    # python2-devel gcc are dependencies of shade
    yum install -y ansible python2-devel gcc

    # dependency of ansible's os_* modules
    pip install shade==1.27.1
}

run_static_analysis() {
    flake8 --statistics --show-source "${SUITE}"
    pylint \
        --rcfile="${SUITE}/pylintrc" \
        --errors-only \
        "${SUITE}/fixtures" \
        "${SUITE}/lib" \
        "${SUITE}/testlib" \
        "${SUITE}/tests"
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
    mkdir -p "${OST_REPO_ROOT}/exported-artifacts"
}

run_tests() {
    local artifacts_path="${OST_REPO_ROOT}/exported-artifacts"
    local junit_xml_path="${artifacts_path}/pytest.junit.xml"

    python -B -m pytest \
        -s \
        -v \
        --durations=0 \
        --log-level=INFO \
        --junit-xml="$junit_xml_path" \
        --lago-env="$PREFIX" \
        --artifacts-path="$artifacts_path" \
        "${SUITE}/tests"
}

run_suite () {
    install_dependencies
    setup_env
    run_static_analysis
    start_env
    run_tests
}
