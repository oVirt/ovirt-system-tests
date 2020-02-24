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
    env_copy_repo_file
    env_copy_config_file
    env_status
    cd "$OST_REPO_ROOT"
    if ! env_deploy; then
        env_collect "$PWD/test_logs/${SUITE##*/}/post-000_deploy"
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi
    declare test_scenarios=($(ls "$SUITE"/test-scenarios/*.py | sort))
    declare failed=false

    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    "${PYTHON}" -m pip install --user -I selenium || echo "ERROR: pip failed, webdriver will fail to connect"

    for scenario in "${test_scenarios[@]}"; do
        echo "Running test scenario ${scenario##*/}"
        env_run_test "$scenario" || failed=true
        if [[ -n "$OST_SKIP_COLLECT" ]]; then
            if [[ "$failed" == "true" ]]; then
                env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario##*/}"
            fi
        else
            env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario##*/}"
        fi
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done

    generate_vdsm_coverage_report
}
