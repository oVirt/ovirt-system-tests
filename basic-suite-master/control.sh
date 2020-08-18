#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

run_suite () {
    install_libguestfs
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    put_host_image
    install_local_rpms_without_reposync
    env_start
    env_dump_ansible_hosts
    env_copy_repo_file
    env_copy_config_file
    env_status
    cd "$OST_REPO_ROOT"
    if ! env_deploy; then
        env_collect "$PWD/test_logs/${SUITE_NAME}/post-000_deploy"
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi
    declare test_scenarios=($(ls "$SUITE"/test-scenarios/*.py | grep -v conftest | sort))
    declare failed=false

    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    "${PYTHON}" -m pip install --user -I selenium || echo "ERROR: pip failed, webdriver will fail to connect"
    "${PYTHON}" -m pip install --user \
        "pytest==4.6.9" \
        "zipp==1.2.0"

    env_run_pytest_bulk ${test_scenarios[@]} || failed=true

    if [[ -z "$OST_SKIP_COLLECT" || "${failed}" == "true" ]]; then
        env_collect "$PWD/test_logs/${SUITE_NAME}"
    fi

    if $failed; then
        echo "@@@@ ERROR: Failed running ${SUITE_NAME}"
        return 1
    fi

    generate_vdsm_coverage_report
}
