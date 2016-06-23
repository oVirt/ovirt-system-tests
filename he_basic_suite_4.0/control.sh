#!/bin/bash -xe
set -o pipefail


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


he_deploy() {
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    cd $PREFIX
    echo "#########################"
    echo "Deploying the host lago_he_basic_suite_4_0_host0"
    lago copy-to-vm \
        lago_he_basic_suite_4_0_host0 \
        "${SUITE}/answers.conf.in" \
        /root/hosted-engine-deploy-answers-file.conf.in

    lago copy-to-vm \
        lago_he_basic_suite_4_0_host0 \
        "${SUITE}/setup_first_he_host.sh" \
        /root/

    lago shell \
        lago_he_basic_suite_4_0_host0 \
        /root/setup_first_he_host.sh

    echo "#########################"
    echo "Deploying the host lago_he_basic_suite_4_0_host1"
    lago copy-to-vm \
        lago_he_basic_suite_4_0_host1 \
        "${SUITE}/answers-additional.conf.in" \
        /root/hosted-engine-deploy-answers-file.conf.in

    lago copy-to-vm \
        lago_he_basic_suite_4_0_host1 \
        "${SUITE}/setup_additional_he_host.sh" \
        /root/

    lago shell \
        lago_he_basic_suite_4_0_host1 \
        /root/setup_additional_he_host.sh
    cd -
}

run_suite(){
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    declare failed=false
    env_init \
        "http://templates.ovirt.org/repo/repo.metadata" \
        "$suite/LagoInitFile"
    env_repo_setup
    env_start
    env_deploy
    he_deploy || failed=true
    if $failed; then
        env_collect "$curdir/test_logs/${suite##*/}/post-he_deploy"
        echo "@@@@ ERROR: Failed running he_deploy"
        return 1
    fi

    declare test_scenarios=($(ls "$suite"/test-scenarios/*.py | sort))

    for scenario in "${test_scenarios[@]}"; do
        echo "Running test scenario ${scenario##*/}"
        env_run_test "$scenario" || failed=true
        env_collect "$curdir/test_logs/${suite##*/}/post-${scenario##*/}"
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            break
        fi
    done
}
