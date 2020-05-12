#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

install_dependencies() {
    yum install -y python-pip
    pip install -U pip==9.0.3
    pip install flake8==3.1.0
    pip install isort==4.2.5 pylint==1.6.4
    pip install pytest==3.5

    pip install contextlib2
    pip install ansible-runner==1.4.4

    yum install -y ansible

    # dependency of ansible's os_* modules
    pip install openstacksdk==0.37
    pip install decorator==4.4.0
}

run_static_analysis() {
    flake8 --statistics --show-source "${SUITE}"
    pylint \
        --rcfile="${SUITE}/pylintrc" \
        --errors-only \
        "${SUITE}/fixtures" \
        "${SUITE}/ovirtlib" \
        "${SUITE}/testlib" \
        "${SUITE}/tests"
}

setup_env() {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    if [[ -e "$SUITE/reposync-config-sdk4.repo" ]]; then
        install_local_rpms_without_reposync
    else
        install_local_rpms
    fi
}

start_env() {
    env_start
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
    generate_vdsm_coverage_report
}
