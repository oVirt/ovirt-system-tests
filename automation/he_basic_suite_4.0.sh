#!/bin/bash

# This script is meant to be run within a mock environment, using
# mock_runner.sh or chrooter, from the root of the repository:
#
# $ cd repository/root
# $ mock_runner.sh -e automation/he_basic_suite_4.0.sh
# or
# $ chrooter -s automation/he_basic_suite_4.0.sh
#

cleanup() {
    rm -rf exported-artifacts
    mkdir -p exported-artifacts
    [[ -d deployment-he_basic_suite_4.0/current/logs ]] \
    && mv deployment-he_basic_suite_4.0/current/logs exported-artifacts/lago_logs
    find deployment-he_basic_suite_4.0 \
        -iname nose\*.xml \
        -exec mv {} exported-artifacts/ \;
    [[ -d test_logs ]] && mv test_logs exported-artifacts/
    ./run_suite.sh --cleanup he_basic_suite_4.0
    exit
}

# needed to run lago inside chroot
export LIBGUESTFS_BACKEND=direct
# uncomment the next lines for extra verbose output
#export LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1
trap cleanup SIGTERM EXIT
res=0

# This is used to test external sources
# it's done by putting them one by line in the ./extra_sources file
extra_sources_cmd=''
if [[ -e ./extra_sources ]]; then
    extra_sources_cmd+="-s \"conf:$PWD/extra_sources\""
fi

./run_suite.sh $extra_sources_cmd he_basic_suite_4.0 \
|| res=$?
exit $res
