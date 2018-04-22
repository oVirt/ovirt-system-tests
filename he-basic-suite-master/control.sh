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
    local he_name="${HOSTEDENGINE:-lago-${suite_name}-engine}"

    HOST=lago-${suite_name}-host-
    cd $PREFIX
    echo "#########################"
    echo "Deploying on ${HOST}0"
    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/answers.conf.in" \
        /root/hosted-engine-deploy-answers-file.conf.in

    lago copy-to-vm \
        ${HOST}0 \
        "${SUITE}/setup_first_he_host.sh" \
        /root/

    lago shell \
        ${HOST}0 \
        /root/setup_first_he_host.sh "$he_name" "$HE_ANSIBLE"
    RET_CODE=$?
    if [ ${RET_CODE} -ne 0 ]; then
        echo "hosted-engine setup on ${HOST}0 failed with status ${RET_CODE}."
        return "${RET_CODE}"
    fi

    lago shell \
	lago-${suite_name}-storage \
        "fstrim -va"

    cd -
}

run_suite(){
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    declare failed=false
    env_init \
        "$1" \
        "$suite/LagoInitFile"
    cd $PREFIX
    lago ovirt reposetup \
        --reposync-yum-config ${suite}/reposync-he.repo
    cd -
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

    declare test_scenarios=($(ls "$suite"/test-scenarios/*.py | sort))

    for scenario in "${test_scenarios[@]}"; do
        echo "Running test scenario ${scenario##*/}"
        env_run_test "$scenario" || failed=true
        env_collect "$curdir/test_logs/${suite##*/}/post-${scenario##*/}"
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done
}
