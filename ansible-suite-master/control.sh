#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
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
    # Verify the ansible_hosts file
    $CLI ansible_hosts >> ansible_hosts_file
    if ansible-playbook \
	--ssh-common-args '-o ControlPath=None -o CheckHostIP=no -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o AddressFamily=inet' \
        --list-hosts \
        -i ansible_hosts_file \
        $SUITE/engine.yml \
        | grep 'hosts (0):'; then
            echo "@@@@ ERROR: ansible: No matching hosts were found"
            return 1
    fi
    trap cleanup_run EXIT SIGHUP SIGTERM
    $CLI ovirt serve & ansible-playbook -u root --ssh-common-args '-o ControlPath=None -o CheckHostIP=no -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o AddressFamily=inet' -i ansible_hosts_file $SUITE/engine.yml --extra-vars='lago_cmd=$CLI prefix=$PREFIX/current log_dir=$PWD/test_logs/${SUITE##*/}/'
}
