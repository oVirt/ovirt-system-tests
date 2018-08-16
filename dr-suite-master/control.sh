#!/usr/bin/env bash

prep_suite () {
    get_orb "https://templates.ovirt.org/bundles/ovirt-demo-tool/4.2/unstable/4.2.4-1.2.g4f465f2/ovirt-orb-4.2.4-1.2.g4f465f2.tar.xz"
    sed -i 's/memory: 2047/memory: 8192/g' "${SUITE}/LagoInitFile"
}

run_suite () {
    env_init \
        "$1" \
        "$SUITE/LagoInitFile"
    env_ovirt_start
    env_status
    declare test_scenarios=($(ls "$SUITE"/test-scenarios/*.py | sort))
    declare failed=false

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
}
