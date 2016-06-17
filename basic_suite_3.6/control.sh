#!/usr/bin/env bash

prep_suite () {
    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./_}"
    sed \
        -e "s,\(^[[:space:]]*\)\(engine\):,\1lago_${suite_name}_\2:,g" \
        -e "s,\(^[[:space:]]*\)\(host[[:digit:]]\+\):,\1lago_${suite_name}_\2:,g" \
        -e "s,\(^[[:space:]]*\)\(lago\):,\1lago_${suite_name}_\2:,g" \
        -e "s,\(^[[:space:]]*\)\(storage[^:]*\):,\1lago_${suite_name}_\2:,g" \
        -e "s,- lago:,- lago_${suite_name}_lago:,g" \
        -e "s,- net: lago,- net: lago_${suite_name}_lago,g" \
    < ${SUITE}/LagoInitFile.in \
    > ${SUITE}/LagoInitFile
}

run_suite () {
    env_init \
        "http://templates.ovirt.org/repo/repo.metadata" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    env_start
    env_deploy

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
}
