#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

run_suite () {
    cd "$OST_REPO_ROOT" && pip install --user -e ost_utils
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    put_host_image
    install_local_rpms
    env_start
    env_status
    if ! env_deploy; then
        env_collect "$PWD/test_logs/${SUITE##*/}/post-000_deploy"
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi
    declare test_scenarios=($(ls "$SUITE"/test-scenarios/*.py | sort))
    declare failed=false
    for scenario in "${test_scenarios[@]}"; do
        echo "Running test scenario ${scenario##*/}"
        env_run_test "$scenario" || failed=true
        env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario##*/}"
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done

    generate_vdsm_coverage_report
}
