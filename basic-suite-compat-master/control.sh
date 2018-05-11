#!/usr/bin/env bash

source $(dirname "$SUITE")/basic-suite-master/control.sh
eval "orig_$(declare -f run_suite)"

run_suite () {
    export OST_DC_VERSION
    for OST_DC_VERSION in 3.6 4.0 4.1 4.2; do
      orig_run_suite
      env_cleanup
    done
}
