#!/usr/bin/env bash

prep_suite () {
    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./-}"
    local engine hosts
    source "${SUITE}/templates"
    sed -r \
        -e "s,__ENGINE__,lago-${suite_name}-engine,g" \
        -e "s,__HOST([0-9]+)__,lago-${suite_name}-host\1,g" \
        -e "s,__LAGO_NET_([A-Za-z0-9]*)__,lago-${suite_name}-net-\L\1,g" \
        -e "s,__STORAGE__,lago-${suite_name}-storage,g" \
        -e "s,__ENGINE_TEMPLATE__,${engine:?},g" \
        -e "s,__HOSTS_TEMPLATE__,${hosts:?},g" \
    < ${SUITE}/LagoInitFile.in \
    > ${SUITE}/LagoInitFile
}

run_suite () {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    [[ -n $RPMS_TO_INSTALL ]] && install_local_rpms
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
}
