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
    env_init
    env_repo_setup
    env_start
    env_deploy

    for script in $(find $SUITE/test-scenarios -type f -name '*.py' | sort); do
        echo "Running script " $(basename $script)
        env_run_test $script
        env_collect $PREFIX/test_logs/post-$(basename $script)
    done
}
