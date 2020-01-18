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
    echo "Running ansible role on ${HOST}1 to deploy on ${HOST}0"

   lago copy-to-vm \
        ${HOST}1 \
        "${SUITE}/hosted_engine_deploy.yml.in" \
        /root/hosted_engine_deploy.yml.in

    lago copy-to-vm \
        ${HOST}1 \
        "${SUITE}/he_deployment.json.in" \
        /root/he_deployment.json.in

    lago copy-to-vm \
        ${HOST}1 \
        "${SUITE}/run_ansible_controller.sh" \
        /root/

    lago shell \
        ${HOST}1 \
        "ssh-keygen -t rsa -N '' -f /root/.ssh/id_rsa"

    lago copy-from-vm \
        ${HOST}1 \
        "/root/.ssh/id_rsa.pub" \
        host1_id_rsa.pub

    lago copy-to-vm \
        ${HOST}0 \
        "host1_id_rsa.pub" \
        /root/

    lago shell \
        ${HOST}0 \
        "cat /root/host1_id_rsa.pub >> /root/.ssh/authorized_keys"

    lago shell \
        ${HOST}1 \
        "ssh-keyscan -H ${HOST}0 >> ~/.ssh/known_hosts"

    # FIXME: workaround for IPv6 on Lago, remove once lago properly supports IPv6
    lago shell \
        ${HOST}0 \
        "sysctl -w net.ipv6.conf.all.disable_ipv6=1"
    end of IPv6 workaround

    lago shell \
        ${HOST}1 \
        /root/run_ansible_controller.sh "$he_name" "${HOST}0"
    RET_CODE=$?
    if [ ${RET_CODE} -ne 0 ]; then
        echo "hosted-engine setup from ${HOST}1 to ${HOST}0 failed with status ${RET_CODE}."
        return "${RET_CODE}"
    fi

    lago shell \
        lago-${suite_name}-storage \
        "fstrim -va"

    cd -
}

run_suite(){
    install_libguestfs
    cd "$OST_REPO_ROOT" && pip install --user -e ost_utils
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    declare failed=false
    env_init \
        "$1" \
        "$suite/LagoInitFile"
    cd $PREFIX
    env_repo_setup
    install_local_rpms_without_reposync
    env_start
    env_copy_repo_file
    env_copy_config_file
    cd "$OST_REPO_ROOT"
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

    generate_vdsm_coverage_report
}
