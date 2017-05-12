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


env_repo_setup_base_version () {
    ci_msg_if_fails $FUNCNAME
    #This function is setting up the env with stable release repo
    echo "######## Setting up repos (init)"
    cd $PREFIX #PREFIX is the dir for the lago env
    #Set the repository for the pre-upgrade deploy
    local reposync_conf="$SUITE/pre-reposync-config.repo"
    echo "using reposync config file: $reposync_conf"
    $CLI ovirt reposetup \
        --reposync-yum-config "$reposync_conf"
    cd -
}


env_repo_setup_destination_version () {
    #The env_repo_setup serves this control
    #This function is for readability purpose only
    env_repo_setup
}


clean_internal_repo () {
    echo "Cleaning internal repo"
    rm -rf "$PREFIX"/default/internal_repo
}


run_suite () {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup_base_version
    install_local_rpms
    env_start
    if ! env_deploy; then
        env_collect "$PWD/test_logs/${SUITE##*/}/post-000_deploy"
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi
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

    #Clean internal repo
    clean_internal_repo
    #Prepare env for upgrade
    env_repo_setup_destination_version
    #This loop runs the engine upgrade and the tests following it
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
