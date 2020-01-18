#!/usr/bin/env bash

prep_suite () {
    render_jinja_templates
}

env_copy_config_file() {

    local file_name="$1"
    local dest_file="$2"
    local run_file="$3"
    cd "$PREFIX"
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
       if [[ -e "$file_name" ]] ;then
           "$CLI" copy-to-vm "$vm" "$file_name" "$dest_file"
       fi
       if [[ -e "$run_file" ]] ;then
           "source $dest_path/${file_name##*/}"
       fi
    done
}

env_copy_repo_file() {

    local engine_repo_file="$1"
    local host_repo_file="$2"
    local copy_to_path="$3"
    cd "$PREFIX"
    ## ENGINE
    local reposync_file="$engine_repo_file"
    local reqsubstr="engine"
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
        if [[ -z "${vm##*$reqsubstr*}" ]] ;then
            if [[ -e "$reposync_file" ]] ;then
                "$CLI" copy-to-vm "$vm" "$reposync_file" "$copy_to_path/${reposync_file##*/}"
            fi
        fi
    done

    ## HOST
    local reposync_file="$host_repo_file"
    local reqsubstr="host"
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
        if [[ -z "${vm##*$reqsubstr*}" ]] ;then
            if [[ -e "$reposync_file" ]] ;then
                "$CLI" copy-to-vm "$vm" "$reposync_file" "$copy_to_path/${reposync_file##*/}"
            fi
        fi
    done

    cd -
}

env_repo_setup_base_version () {
    #This function is setting up the env with stable release repo
    echo "######## Setting up repos (init)"
    cd $PREFIX #PREFIX is the dir for the lago env
    #Set the repository for the pre-upgrade deploy
    local reposync_conf="$SUITE/pre-reposync-config.repo"
    echo "using reposync config file: $reposync_conf"
    $CLI ovirt reposetup \
        --reposync-yum-config "$reposync_conf"
    cd -
}

env_repo_setup_destination_version () {
    #The env_repo_setup serves this control
    #This function is for readability purpose only
    env_repo_setup
}

run_cli_on_vms () {

    local command="$1"
    cd "$PREFIX"
    for vm in $(lago --out-format flat status | \
        gawk 'match($0, /^VMs\/(.*)\/status:*/, m){ print m[1]; }')\
        ; do

        echo "$vm"
       "$CLI" shell "$vm" -c "$command"
    done
}

clean_internal_repo () {
    echo "Cleaning internal repo"
    rm -rf "$PREFIX"/default/internal_repo
}

run_suite () {
    cd "$OST_REPO_ROOT" && pip install --user -e ost_utils
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_repo_setup_base_version
    if [[ -e "$SUITE/reposync-config-sdk4.repo" ]] ;then
        install_local_rpms_without_reposync
    else
        install_local_rpms
    fi
    #install_local_rpms
    env_start
    env_copy_config_file "$SUITE/vars/main.yml" "/tmp/vars_main.yml" false
    env_copy_repo_file "$SUITE"/pre-reposync-config-engine.repo \
        "$SUITE"/pre-reposync-config-host.repo \
        "/etc/yum.repos.d"
    cd "$OST_REPO_ROOT"
    if ! env_deploy; then
        env_collect "$PWD/test_logs/${SUITE##*/}/post-000_deploy"
        echo "@@@ ERROR: Failed in deploy stage"
        return 1
    fi
    declare test_scenarios_before=($(ls "$SUITE"/test-scenarios-before-upgrade/*.py | sort))
    declare test_scenarios_after=($(ls "$SUITE"/test-scenarios-after-upgrade/*.py | sort))
    declare failed=false

    #This loop is for the tests BEFORE the engine upgrade
    for scenario_b in "${test_scenarios_before[@]}"; do
        echo "Running test scenario ${scenario_b##*/}"
        env_run_test "$scenario_b" || failed=true
        env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario_b##*/}"
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario_b"
            return 1
        fi
    done

    #Clean internal repo
    clean_internal_repo
    if [[ -e "$SUITE/pre-reposync*.repo" ]] ; then
        # disable old repos
        run_cli_on_vms "yum-config-manager --disable \*"
        # remove old repo files
        run_cli_on_vms "rm /etc/yum.repos.d/pre-reposync*.repo"
    fi
    # copy repo file to VM's
    env_copy_repo_file "$SUITE"/reposync-config-engine.repo \
        "$SUITE"/reposync-config-host.repo \
        "/etc/yum.repos.d"
    # install the new release_rpm
    if [[ -e "$SUITE/deploy-scripts/post_general_add_local_repo.sh" ]] ; then
        env_copy_config_file "$SUITE/deploy-scripts/post_general_add_local_repo.sh" \
            "/tmp/post_add_local_repo.sh" \
            true

        # run the script
        run_cli_on_vms "source /tmp/post_add_local_repo.sh"
    fi
    #Prepare env for upgrade
    env_repo_setup_destination_version
    #This loop runs the engine upgrade and the tests following it
    for scenario_a in "${test_scenarios_after[@]}"; do
        echo "Running test scenario ${scenario_a##*/}"
        env_run_test "$scenario_a" || failed=true
        env_collect "$PWD/test_logs/${SUITE##*/}/post-${scenario_a##*/}"
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done
}
