#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

run_suite () {
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

    # use a virtualenv and install selenium via pip, because there is no maintained rpm available
    venv=$(mktemp -d)
    virtualenv --system-site-packages "$venv"
    source $venv/bin/activate
    pip install -I selenium || echo "ERROR: pip failed, webdriver will fail to connect"
    export PYTHONPATH="${PYTHONPATH}:${venv}/lib/python2.7/site-packages"

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
    deactivate
}
