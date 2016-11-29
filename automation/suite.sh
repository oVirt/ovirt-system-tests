#!/bin/bash -xe

# This script is meant to be run within a mock environment, using
# mock_runner.sh or chrooter, from the root of the repository:
#
# $ cd repository/root
# $ mock_runner.sh -e automation/basic_suite_4.0.sh
# or
# $ chrooter -s automation/basic_suite_4.0.sh
#

SUITE="$0"
SUITE=$(echo "$SUITE" | tr '_' '-')
# Leaving just the base dir
SUITE=${SUITE##*/}
# Remove file extension
SUITE=${SUITE%.*}
echo "Running suite: $SUITE"

SUITE_REAL_PATH=$(realpath "$SUITE")

cleanup() {
    rm -rf exported-artifacts
    mkdir -p exported-artifacts
    [[ -d deployment-$SUITE/current/logs ]] \
    && mv "deployment-$SUITE/current/logs" exported-artifacts/lago_logs
    find "deployment-$SUITE" \
        -iname nose\*.xml \
        -exec mv {} exported-artifacts/ \;
    [[ -d test_logs ]] && mv test_logs exported-artifacts/
    [[ -e failure_msg.txt ]] && mv failure_msg.txt exported-artifacts/
    ./run_suite.sh --cleanup "$SUITE"
    exit
}

# needed to run lago inside chroot
export LIBGUESTFS_BACKEND=direct
# uncomment the next lines for extra verbose output
#export LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1
trap cleanup SIGTERM EXIT
res=0

# This is used to test external sources
# it's done by putting them one per line in $SUITE/extra-sources file, the
# It will look for:
# 1. $SUITE/extra_sources
# 2. $PWD/extra_sources
# Example:
# > cat extra_sources
# http://plain.resources.ovirt.org/repos/ovirt/experimental/master/latest.under_testing/
#
extra_sources_cmd=""
if [[ -e "$SUITE_REAL_PATH/extra_sources" ]]; then
    cat "$SUITE_REAL_PATH/extra_sources"
    extra_sources_cmd="-s \"conf:$SUITE_REAL_PATH/extra_sources\""
elif [[ -e "$PWD/extra_sources" ]]; then
    cat "$PWD/extra_sources"
    extra_sources_cmd="-s \"conf:$PWD/extra_sources\""
fi

if [[ -z "$extra_sources_cmd" ]]; then
    ./run_suite.sh "$SUITE" || res=$?
else
    ./run_suite.sh "$extra_sources_cmd" "$SUITE" || res=$?
fi
exit $res
