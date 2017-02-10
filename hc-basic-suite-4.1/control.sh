#!/bin/bash -xe
set -o pipefail

prep_suite () {
    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./-}"
    sed -r \
        -e "s,__ENGINE__,lago-${suite_name}-engine,g" \
        -e "s,__HOST([0-9]+)__,lago-${suite_name}-host\1,g" \
        -e "s,__LAGO_NET_([A-Za-z0-9]*)__,lago-${suite_name}-net-\L\1,g" \
        -e "s,__STORAGE__,lago-${suite_name}-storage,g" \
    < ${SUITE}/LagoInitFile.in \
    > ${SUITE}/LagoInitFile
}

he_deploy() {
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./-}"
    HOST=lago-${suite_name}-host
    VMPASS=123456
    cd $PREFIX

    echo "#########################"
    echo "Setting up passwordless ssh"
    lago shell \
        ${HOST}0 \
        ssh-keygen -t rsa -f /root/.ssh/id_rsa -N \"\"
    
    lago shell \
        ${HOST}0 \
        sshpass \
        -p "${VMPASS}" \
        ssh-copy-id -o StrictHostKeyChecking=no -i ${HOST}0

    lago shell \
        ${HOST}0 \
        sshpass \
        -p "${VMPASS}" \
        ssh-copy-id -o StrictHostKeyChecking=no -i ${HOST}1

    lago shell \
        ${HOST}0 \
        sshpass \
        -p "${VMPASS}" \
        ssh-copy-id -o StrictHostKeyChecking=no -i ${HOST}2

    echo "#########################"
    echo "Deploying on ${HOST}0"
    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/robo.conf.in" \
        /root/robo.conf.in

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/hc-answers.conf.in" \
        /root/hc-answers.conf.in

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/gdeploy.sh" \
        /root/gdeploy.sh

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/generate-hc-answerfile.sh" \
        /root/generate-hc-answerfile.sh

    lago shell \
        ${HOST}0 \
        /root/gdeploy.sh ${HOST}0 ${HOST}1 ${HOST}2

    RET_CODE=$?
    if [ ${RET_CODE} -ne 0 ]; then
        echo "gdeploy setup on ${HOST}0 failed with status ${RET_CODE}."
        exit ${RET_CODE}
    fi
    cd -
}


run_suite () {
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    declare failed=false
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    env_start
    env_deploy
    he_deploy || failed=true
    if $failed; then
        env_collect "$curdir/test_logs/${suite##*/}/post-he_deploy"
        echo "@@@@ ERROR: Failed running he_deploy"
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
