#!/bin/bash

# This script is meant to be run within a mock environment, using
# mock_runner.sh or chrooter, from the root of the repository:
#
# $ cd repository/root
# $ mock_runner.sh -e automation/basic_suite_3.5.sh
# or
# $ chrooter -s automation/basic_suite_3.5.sh
#

cleanup() {
    ./run_suite.sh --cleanup basic_suite_3.5
    exit
}

# needed to run lago inside chroot
export LIBGUESTFS_BACKEND=direct
# uncomment the next lines for extra verbose output
#export LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1
trap cleanup SIGTERM EXIT
res=0
./run_suite.sh basic_suite_3.5 \
|| res=$?
exit $res
