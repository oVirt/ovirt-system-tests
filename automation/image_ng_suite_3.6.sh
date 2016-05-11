#!/bin/bash -xe

# This script is meant to be run within a mock environment, using
# mock_runner.sh or chrooter, from the root of the repository:
#
# $ cd repository/root
# $ mock_runner.sh -e automation/basic_suite_3.5.sh
# or
# $ chrooter -s automation/basic_suite_3.5.sh
#

cleanup() {
    rm -rf exported-artifacts
    mkdir -p exported-artifacts
    [[ -d deployment-image_ng_suite_3.6/current/logs ]] \
    && mv deployment-image_ng_suite_3.6/current/logs exported-artifacts/lago_logs
    find deployment-image_ng_suite_3.6 \
        -iname nose\*.xml \
        -exec mv {} exported-artifacts/ \;
    [[ -d test_logs ]] && mv test_logs exported-artifacts/
    ./run_suite.sh --cleanup image_ng_suite_3.6
    exit
}

# needed to run lago inside chroot
export LIBGUESTFS_BACKEND=direct

#Turn on the next 3 lines for virt debug
#export LIBGUESTFS_DEBUG=1
#export LIBGUESTFS_TRACE=1
#libguestfs-test-tool

# Hack sudo to ignore tty
sed -i -e 's/Defaults    requiretty.*/ #Defaults    requiretty/g' /etc/sudoers

trap cleanup SIGTERM EXIT
res=0

shopt -s nullglob

node=(images/exported-artifacts/*squashfs.img)
engine=(images/exported-artifacts/*.ova)

./run_suite.sh image_ng_suite_3.6 \
    -n "$node" \
    -e "$engine" \
|| res=$?
exit $res
