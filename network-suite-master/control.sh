#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

install_dependencies() {
    "${PYTHON}" -m pip install \
        "pytest==3.5" \
        "openstacksdk==0.37"
    "${PYTHON}" -m pip install --user -e "$OST_REPO_ROOT"/ost_utils
}

setup_env() {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
}

start_env() {
    env_start
    env_dump_ansible_hosts
    env_wait_for_ssh
    env_add_extra_repos
    env_status
    mkdir -p "${OST_REPO_ROOT}/exported-artifacts"
}

run_tests() {
    local artifacts_path="${OST_REPO_ROOT}/exported-artifacts"
    local junit_xml_path="${artifacts_path}/pytest.junit.xml"

    "${PYTHON}" -B -m pytest \
        -s \
        -v \
        --durations=0 \
        --log-level=INFO \
        --junit-xml="$junit_xml_path" \
        "${SUITE}/test-scenarios"
}

run_suite () {
    install_dependencies
    setup_env
    start_env
    run_tests
}
