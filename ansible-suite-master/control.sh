#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

run_suite () {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    install_local_rpms_without_reposync
    env_start
    env_dump_ansible_hosts
    env_wait_for_ssh
    env_add_extra_repos
    env_copy_repo_file
    env_copy_config_file
    env_status
    env_ansible
    cd "$OST_REPO_ROOT"
    if ! env_deploy; then
        env_collect "$PWD/test_logs/${SUITE##*/}/post-000_deploy"
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi

    declare failed=false

    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    "${PYTHON}" -m pip install --user \
        "importlib_metadata==2.0.0" \
        "pytest==4.6.9" \
        "zipp==1.2.0"

    env_run_pytest_bulk "${SUITE}/test-scenarios" || failed=true

    if [[ -z "$OST_SKIP_COLLECT" || "${failed}" == "true" ]]; then
        env_collect "$PWD/test_logs/${SUITE_NAME}"
    fi

    if $failed; then
        echo "@@@@ ERROR: Failed running ${SUITE_NAME}"
        return 1
    fi

    LOGS_DIR="$PWD/test_logs"
    export ANSIBLE_CONFIG="${SUITE}/ansible.cfg"
    cd $PREFIX/current

    if ansible-playbook \
        --list-hosts \
        -i ${ANSIBLE_INVENTORY_FILE} \
        $SUITE/engine.yml \
        | grep 'hosts (0):'; then
            echo "@@@@ ERROR: ansible: No matching hosts were found"
            return 1
    fi
    ansible-playbook -v -u root -i ${ANSIBLE_INVENTORY_FILE} $SUITE/engine.yml --extra-vars="lago_cmd=$CLI prefix=$PREFIX/current log_dir=$LOGS_DIR/${SUITE##*/}/"
}
