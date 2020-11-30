#!/bin/bash -xe
set -o pipefail

prep_suite () {
    render_jinja_templates
}

env_copy_config_file() {

    cd "$PREFIX"
    reqsubstr=$1
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
        if [[ -z "${vm##*$reqsubstr*}" ]] ;then
            "$CLI" copy-to-vm "$vm" "$SUITE/vars/main.yml" "/tmp/vars_main.yml"
        fi
    done
    cd -
}

env_copy_repo_file() {

    cd "$PREFIX"
    host_type=$1
    local reposync_file="reposync-config-${host_type}.repo"
    local reqsubstr=$host_type
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
        if [[ -z "${vm##*$reqsubstr*}" ]] ;then
            if [[ -e "$SUITE/$reposync_file" ]]; then
                "$CLI" copy-to-vm "$vm" "$SUITE/$reposync_file" "/etc/yum.repos.d/$reposync_file"
            fi
        fi
    done
    cd -
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

    lago shell \
        ${HOST}0 \
        rm -rf /etc/ansible/roles/*

    lago shell \
        ${HOST}0 \
        yum install https://copr-be.cloud.fedoraproject.org/results/sac/gluster-ansible/epel-7-x86_64/00905703-gluster-ansible/gluster-ansible-1.0.5-1.el7.noarch.rpm -y

    echo "#########################"
    echo "Running ansible playbook on ${HOST}0"
    if [[ -e "${SUITE}/gluster_inventory.yml.in" ]]; then
        lago copy-to-vm \
            ${HOST}0 \
            "${SUITE}/gluster_inventory.yml.in" \
            /root/gluster_inventory.yml.in
    fi
    if [[ -e "${SUITE}/ohc_gluster_inventory.yml.in" ]]; then
        lago copy-to-vm \
            ${HOST}0 \
            "${SUITE}/ohc_gluster_inventory.yml.in" \
            /root/ohc_gluster_inventory.yml.in
    fi

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/ohc_he_gluster_vars.json.in" \
        /root/ohc_he_gluster_vars.json.in

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/exec_playbook.sh" \
        /root/exec_playbook.sh

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
    cd "$OST_REPO_ROOT" && pip install --user -e ost_utils
    install_libguestfs
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    if [[ -e "$SUITE/reposync-config-sdk4.repo" ]]; then
        install_local_rpms_without_reposync
    else
        install_local_rpms
    fi
    env_start
    env_copy_config_file "host"
    env_copy_repo_file "host"
    env_status
    cd "$OST_REPO_ROOT"
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
