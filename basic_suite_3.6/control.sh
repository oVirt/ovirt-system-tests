#!/usr/bin/env bash

prep_suite () {
    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./_}"
    sed -r \
        -e "s,__ENGINE__,lago_${suite_name}_engine,g" \
        -e "s,__HOST([0-9]+)__,lago_${suite_name}_host\1,g" \
        -e "s,__LAGO_NET__,lago_${suite_name}_lago,g" \
        -e "s,__STORAGE__,lago_${suite_name}_storage,g" \
    < ${SUITE}/LagoInitFile.in \
    > ${SUITE}/LagoInitFile
}

run_suite () {
    env_init \
        "$1" \
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
