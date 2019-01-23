#!/usr/bin/env bash

prep_suite() {
    :
}

run_suite() {
    env_repo_setup
    install_local_rpms
    env_start
    env_status

    # TODO: Upload the vagrant vm images to the engine so the test can use it.
    #put_host_image
    declare test_scenarios=($(ls "$SUITE"/test-scenarios/*.py | sort))
    declare failed=false

    for scenario in "${test_scenarios[@]}"; do
        echo "Running test scenario ${scenario##*/}"
        env_run_test "$scenario" || failed=true
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done

    generate_vdsm_coverage_report
    deactivate
}
