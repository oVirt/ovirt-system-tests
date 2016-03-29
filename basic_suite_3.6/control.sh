#!/usr/bin/env bash

prep_suite () {
    #TODO: Properly parste the json to add the prefix to the virt entitites
    #      or better, https://bugzilla.redhat.com/show_bug.cgi?id=1278536
    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./_}"
    sed \
        -e "s,@SUITE@,${SUITE},g" \
        -e "s,\(^[[:space:]]*\)\"\(engine\)\",\1\"lago_${suite_name}_\2\",g" \
        -e "s,\(^[[:space:]]*\)\"\(host[[:digit:]]\+\)\",\1\"lago_${suite_name}_\2\",g" \
        -e "s,\(^[[:space:]]*\)\"\(lago\)\",\1\"lago_${suite_name}_\2\",g" \
        -e "s,\(^[[:space:]]*\)\"\(storage[^\"]*\)\",\1\"lago_${suite_name}_\2\",g" \
        -e "s,\"net\": \"lago\",\"net\": \"lago_${suite_name}_lago\",g" \
    < ${SUITE}/init.json.in \
    > ${SUITE}/init.json
}

run_suite () {
    env_init "http://templates.ovirt.org/repo/repo.metadata"
    env_repo_setup
    env_start
    env_deploy

    test_scenarios=($(ls "$SUITE"/test-scenarios/*.py | sort))

    for scenario in "${test_scenarios[@]}"; do
        echo "Running test scenario ${scenario##*/}"
        env_run_test "$scenario"
        env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario##*/}"
    done
}
