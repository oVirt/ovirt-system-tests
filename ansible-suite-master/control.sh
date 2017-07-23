#!/usr/bin/env bash
ANSIBLE_HOSTS_FILE="ansible_hosts"

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

cleanup_run() {
    lago_serve_pid=$!
    rm -f /tmp/ansible.cfg
    kill $lago_serve_pid
    cd -
}

run_suite () {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    env_start
    env_status
    env_ansible
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
        break
    done

    cd $PREFIX/current
    # SSH ControlPath can have max 108 chars. Ansible default path is $HOME/.ansible/cp
    # which in jenkins is 105 chars
    mkdir -p /tmp/.ansible/cp/
    echo -e "[ssh_connection]\ncontrol_path=None" > /tmp/ansible.cfg
    # Verify the ansible_hosts file
    if ansible-playbook \
        --list-hosts \
        -i ansible_hosts \
        $SUITE/engine.yml \
        | grep 'hosts (0):'; then
            echo "@@@@ ERROR: ansible: No matching hosts were found"
            return 1
    fi
    trap cleanup_run EXIT SIGHUP SIGTERM
    $CLI ovirt serve & ANSIBLE_CONFIG=/tmp/ansible.cfg ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i $ANSIBLE_HOSTS_FILE $SUITE/engine.yml --extra-vars='lago_cmd=$CLI prefix=$PREFIX/current log_dir=$PWD/test_logs/${SUITE##*/}/'
}
