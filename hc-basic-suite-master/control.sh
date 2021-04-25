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
    IDENENTITY_KEY="/etc/ssh/ssh_host_rsa_key"
    cd $PREFIX

    lago shell \
        ${HOST}0 \
        sshpass \
        -p "${VMPASS}" \
        ssh-copy-id -o StrictHostKeyChecking=no \
        -i ${IDENENTITY_KEY}.pub ${HOST}0

    lago shell \
        ${HOST}0 \
        sshpass \
        -p "${VMPASS}" \
        ssh-copy-id -o StrictHostKeyChecking=no \
        -i ${IDENENTITY_KEY}.pub ${HOST}1

    lago shell \
        ${HOST}0 \
        sshpass \
        -p "${VMPASS}" \
        ssh-copy-id -o StrictHostKeyChecking=no \
        -i ${IDENENTITY_KEY}.pub ${HOST}2

    lago shell \
        ${HOST}0 \
        mkdir \
        /etc/ovirt-host-deploy.conf.d/

    lago shell \
        ${HOST}1 \
        mkdir \
        /etc/ovirt-host-deploy.conf.d/

    lago shell \
        ${HOST}2 \
        mkdir \
        /etc/ovirt-host-deploy.conf.d/

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
        /root/exec_playbook.sh ${HOST}0 ${HOST}1 ${HOST}2 ${IDENENTITY_KEY}

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
    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_add_extra_repos
    env_start
    env_dump_ansible_hosts
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

    "${PYTHON}" -m pip install --user "pytest==6.2.2"

    declare test_scenarios="${SUITE}/test-scenarios"
    declare failed=false

    env_run_pytest_bulk "$test_scenarios" || failed=true

    if $failed; then
        echo "@@@@ ERROR: Failed running ${suite}"
        return 1
    fi
}
