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

    echo "Disabling alocalsync repository"
    lago shell \
        ${HOST}0 \
        "dnf config-manager --set-disabled alocalsync"

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

setup_ipv6() {
    export IPV6_ONLY=True
    export IPV6_SUBNET=$(python "${OST_REPO_ROOT}/he-basic-ipv6-suite-master/find_ipv6_subnet.py" \
    "$PREFIX" "lago-${SUITE##*/}-net-mgmt-ipv6")
}

run_suite(){
    cd "$OST_REPO_ROOT" && "${PYTHON}" -m pip install --user -e ost_utils
    "${PYTHON}" -m pip install --user \
        "importlib_metadata==2.0.0" \
        "pytest==4.6.9" \
        "zipp==1.2.0"

    local suite="${SUITE?}"
    local curdir="${PWD?}"
    declare failed=false
    env_init \
        "$1" \
        "$suite/LagoInitFile"
    env_repo_setup
    if [[ -e "${SUITE}/reposync-config-sdk4.repo" ]]; then
        install_local_rpms_without_reposync
    else
        cd $PREFIX
        lago ovirt reposetup \
            --reposync-yum-config ${suite}/reposync-he.repo
        cd -
        install_local_rpms
    fi
    env_start
    env_dump_ansible_hosts
    env_copy_repo_file
    env_copy_config_file
    cd "$OST_REPO_ROOT"

    if [[ ${suite} == *"ipv6"* ]]; then
        setup_ipv6
    fi

    env_deploy
    he_deploy || failed=true
    if $failed; then
        sleep 600
        env_collect "$curdir/test_logs/${suite##*/}/post-he_deploy"
        echo "@@@@ ERROR: Failed running he_deploy"
        return 1
    fi

    declare test_scenarios=($(ls "$suite"/test-scenarios/*.py | sort))

    for scenario in "${test_scenarios[@]}"; do
        if [[ "$scenario" == *pytest* ]]; then
            echo "Running test scenario ${scenario##*/} with pytest"
            env_run_pytest "$scenario" || failed=true
        else
            echo "Running test scenario: ${scenario##*/}"
            env_run_test "$scenario" || failed=true
        fi
        env_collect "$curdir/test_logs/${suite##*/}/post-${scenario##*/}"
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done

    generate_vdsm_coverage_report
}
