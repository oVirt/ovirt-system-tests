#!/usr/bin/env bash

prep_suite () {
    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./-}"
    sed -r \
        -e "s,__ENGINE__,lago-${suite_name}-engine,g" \
        -e "s,__HOST([0-9]+)__,lago-${suite_name}-host\1,g" \
        -e "s,__LAGO_NET__,lago-${suite_name}-lago,g" \
        -e "s,__STORAGE__,lago-${suite_name}-storage,g" \
    < ${SUITE}/LagoInitFile.in \
    > ${SUITE}/LagoInitFile
}

env_repo_setup_pre_upgrade () {
#This function is setting up the env with stable release repo
    echo "#####Setting up repos (pre upgrade)...#####"
    cd $PREFIX #PREFIX is the dir for the lago env
#Set the repository for the pre-upgrade deploy
    local reposync_conf="$SUITE/reposync-config.repo"
    echo "using reposync config file: $reposync_conf"
    $CLI ovirt reposetup \
        --reposync-yum-config "$reposync_conf"
    cd -
}

run_suite () {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup_pre_upgrade
    env_start
    env_deploy

    declare test_scenarios_before=($(ls "$SUITE"/test-scenarios-before-upgrade/*.py | sort))
    declare test_scenarios_after=($(ls "$SUITE"/test-scenarios-after-upgrade/*.py | sort))
    declare failed=false

#This loop is for the tests BEFORE the engine upgrade
    for scenario_b in "${test_scenarios_before[@]}"; do
        echo "Running test scenario ${scenario_b##*/}"
        env_run_test "$scenario_b" || failed=true
        env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario_b##*/}"
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario_b"
            return 1
        fi
    done

#Clean the internal repo
rm -rf $PREFIX/current/internal_repo/*
echo "Internal repo list:\n"
cd -
#Upgrade the repo

env_repo_setup

#This loop is for the tests AFTER the engine upgrade
    for scenario_a in "${test_scenarios_after[@]}"; do
    echo "Running test scenario ${scenario_a##*/}"
    env_run_test "$scenario_a" || failed=true
    env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario_a##*/}"
    if $failed; then
        echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done
}
