#!/bin/bash -xe
set -o pipefail

prep_suite () {
    render_jinja_templates
}

he_deploy() {
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./-}"
    HOST=lago-${suite_name}-host-
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
    echo "Running ansible playbook on ${HOST}0"
    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/ohc_gluster_inventory.yml.in" \
        /root/ohc_gluster_inventory.yml.in

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/ohc_he_gluster_vars.json.in" \
        /root/ohc_he_gluster_vars.json.in

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/exec_playbook.sh" \
        /root/exec_playbook.sh

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/generate-hc-answerfile.sh" \
        /root/generate-hc-answerfile.sh

    lago shell \
        ${HOST}0 \
        /root/exec_playbook.sh ${HOST}0 ${HOST}1 ${HOST}2

    RET_CODE=$?
    if [ ${RET_CODE} -ne 0 ]; then
        echo "ansible setup on ${HOST}0 failed with status ${RET_CODE}."
        exit ${RET_CODE}
    fi

    lago shell \
	${HOST}0 \
	"fstrim -va"

    lago shell \
	${HOST}1 \
	"fstrim -va"

    lago shell \
	${HOST}2 \
        "fstrim -va"
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
    install_local_rpms
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
