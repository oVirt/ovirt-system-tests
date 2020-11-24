#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

install_dependencies() {
    "${PYTHON}" -m pip install -U pip==9.0.3
    "${PYTHON}" -m pip install contextlib2
    "${PYTHON}" -m pip install \
        "flake8==3.1.0" \
        "isort==4.2.5" \
        "pytest==3.5" \
        "ansible-runner==1.4.4" \
        "decorator==4.4.0" \
        "openstacksdk==0.37"
    install_libguestfs
    "${PYTHON}" -m pip install --user -e "$OST_REPO_ROOT"/ost_utils
}

run_static_analysis_pylint() {
    "${PYTHON}" -m pip install pylint==2.5.3
    "${PYTHON}" -m pylint \
        --rcfile="${SUITE}/pylintrc" \
        --errors-only \
        "${SUITE}/fixtures" \
        "${SUITE}/ovirtlib" \
        "${SUITE}/testlib" \
        "${SUITE}/test-scenarios"
}

run_static_analysis_flake() {
    "${PYTHON}" -m flake8 --statistics --show-source "${SUITE}"
}

setup_env() {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    if [[ ${USE_LAGO_OST_PLUGIN} -eq 1 ]]; then
        env_repo_setup
    fi
    if [[ -e "$SUITE/reposync-config-sdk4.repo" ]]; then
        install_local_rpms_without_reposync
    else
        install_local_rpms
    fi
}

start_env() {
    env_start
    env_dump_ansible_hosts
    if [[ ${USE_LAGO_OST_PLUGIN} -eq 0 ]]; then
        env_wait_for_ssh
        env_add_extra_repos
    fi
    env_copy_repo_file
    env_copy_config_file
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

    "${PYTHON}" -B -m pytest \
        -s \
        -v \
        --durations=0 \
        --log-level=INFO \
        --junit-xml="$junit_xml_path" \
        --artifacts-path="$artifacts_path" \
        "${SUITE}/test-scenarios"
}

run_suite () {
    install_dependencies
    setup_env
    run_static_analysis_flake
    if [[ "${PYTHON}" !=  "python2" ]]; then
        run_static_analysis_pylint
    fi
    start_env
    run_tests
    generate_vdsm_coverage_report
}
