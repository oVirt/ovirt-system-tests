#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

env_copy_config_file() {

    cd "$PREFIX"
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
       "$CLI" copy-to-vm "$vm" "$SUITE/vars/main.yml" "/tmp/vars_main.yml"
    done
}

env_copy_repo_file() {

    cd "$PREFIX"
    ## ENGINE
    local reposync_file="reposync-config-engine.repo"
    local reqsubstr="engine"
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
        if [ -z "${vm##*$reqsubstr*}" ] ;then
            "$CLI" copy-to-vm "$vm" "$SUITE/$reposync_file" "/etc/yum.repos.d/$reposync_file"
        fi
    done

    ## HOST
    local reposync_file="reposync-config-host.repo"
    local reqsubstr="host"
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
        if [ -z "${vm##*$reqsubstr*}" ] ;then
            "$CLI" copy-to-vm "$vm" "$SUITE/$reposync_file" "/etc/yum.repos.d/$reposync_file"
        fi
    done

    cd -
}

run_suite () {
    cd /tmp
    /var/lib/ci_toolbox/safe_download.sh \
        -s ec284cf371566983084a5e0427ed4f7ee48bd981 \
        appliance.lock \
        http://download.libguestfs.org/binaries/appliance/appliance-1.38.0.tar.xz \
        /var/lib/lago/appliance-1.38.0.tar.xz

    tar xvf /var/lib/lago/appliance-1.38.0.tar.xz
    cd -
    export LIBGUESTFS_PATH=/tmp/appliance

    cd "$OST_REPO_ROOT" && pip install --user -e ost_utils
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup
    put_host_image
    install_local_rpms_without_reposync
    env_start
    env_copy_repo_file
    env_copy_config_file
    env_status
    cd "$OST_REPO_ROOT"
    if ! env_deploy; then
        env_collect "$PWD/test_logs/${SUITE##*/}/post-000_deploy"
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi
    declare test_scenarios=($(ls "$SUITE"/test-scenarios/*.py | sort))
    declare failed=false

    # use a virtualenv and install selenium via pip, because there is no maintained rpm available
    venv=$(mktemp -d)
    virtualenv --system-site-packages "$venv"
    source $venv/bin/activate
    cd "$OST_REPO_ROOT" && pip install --user -e ost_utils
    pip install -I selenium || echo "ERROR: pip failed, webdriver will fail to connect"
    export PYTHONPATH="${PYTHONPATH}:${venv}/lib/python2.7/site-packages"

    for scenario in "${test_scenarios[@]}"; do
        echo "Running test scenario ${scenario##*/}"
        env_run_test "$scenario" || failed=true
        if [[ -n "$OST_SKIP_COLLECT" ]]; then
            if [[ "$failed" == "true" ]]; then
                env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario##*/}"
            fi
        else
            env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario##*/}"
        fi
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done

    generate_vdsm_coverage_report
    deactivate
}
