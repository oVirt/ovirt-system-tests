#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

install_dependencies() {
    "${PYTHON}" -m tox -e deps
    source "${OST_REPO_ROOT}/.tox/deps/bin/activate"
}

setup_env() {
    env_init \
        "$1" \
        "${OST_REPO_ROOT}/${SUITE}/LagoInitFile"
}

start_env() {
    env_start
    env_dump_ansible_hosts
    env_status
    mkdir -p "${OST_REPO_ROOT}/exported-artifacts"
}

run_tests() {
    local artifacts_path="${OST_REPO_ROOT}/exported-artifacts"
    local junit_xml_path="${artifacts_path}/pytest.junit.xml"

    CUSTOM_REPOS_ARGS=()
    for custom_repo in ${EXTRA_SOURCES[@]}; do
        CUSTOM_REPOS_ARGS+=("--custom-repo=${custom_repo}")
    done

    "${PYTHON}" -B -m pytest \
        -s \
        -v \
        --durations=0 \
        --setup-show \
        --log-level=INFO \
        --junit-xml="$junit_xml_path" \
        ${CUSTOM_REPOS_ARGS[@]} \
        "${OST_REPO_ROOT}/${SUITE}/test-scenarios"
}

run_suite () {
    install_dependencies
    setup_env
    start_env
    run_tests
}
