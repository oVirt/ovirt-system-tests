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

# Default RPMs to install in the mock env.
# Unlike the RPMs from .packages file, this RPMs will be taken from lago's
# internal repo (assuming that we have a newer version in the internal repo).
DEFAULT_RPMS=(ovirt-engine-sdk-python python-ovirt-engine-sdk4)

# if above RAM_THRESHOLD KBs are available in /dev/shm, run there
RAM_THRESHOLD=15000000

#Indicate if image creation is needed
readonly CREATE_IMAGES="$PWD/CREATE_IMAGES.marker"

get_run_path() {
    local avail_shm
    avail_shm=$(df --output=avail /dev/shm | sed 1d)
    [[ "$avail_shm" -ge "$RAM_THRESHOLD" ]] && \
        mkdir -p "/dev/shm/ost" && \
        echo "/dev/shm/ost/deployment-$SUITE" || \
        echo "$PWD/deployment-$SUITE"
}

cleanup() {
    local run_path="$1"

    echo "suite.sh: moving artifacts"

    # collect lago.log
    [[ -d "$run_path/current/logs" ]] \
    && mv "$run_path/current/logs" exported-artifacts/lago_logs

    # collect exported images
    [[ -d exported_images ]] \
    && find exported_images \
        -iname \*.tar.xz \
        -exec mv {} exported-artifacts/ \; \
    && find exported_images \
        -iname \*.md5 \
        -exec mv {} exported-artifacts/ \;

    # collect nose junit reports
    [[ -d "$run_path" ]] \
    && find "$run_path" \
        -type f \
        -iname "*.junit.xml" \
        -exec mv {} exported-artifacts/ \;

    # collect the logs that were collected from lago's vms
    [[ -d "test_logs" ]] && mv test_logs exported-artifacts/

    ./run_suite.sh -o "$run_path" --cleanup "$SUITE"
    exit
}

# needed to run lago inside chroot
# TO-DO: use libvirt backend instead
export LIBGUESTFS_BACKEND=direct
# ensure /dev/kvm exists, otherwise it will still use
# direct backend, but without KVM(much slower).
! [[ -c "/dev/kvm" ]] && mknod /dev/kvm c 10 232
# uncomment the next lines for extra verbose output
#export LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1

rm -rf exported-artifacts
mkdir -p exported-artifacts

run_path=$(get_run_path)
trap 'cleanup "$run_path"' SIGTERM SIGINT SIGQUIT EXIT
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
extra_cmds=()
if [[ -e "$SUITE_REAL_PATH/extra_sources" ]]; then
    cat "$SUITE_REAL_PATH/extra_sources"
    extra_cmds+=(-s "conf:$SUITE_REAL_PATH/extra_sources")
elif [[ -e "$PWD/extra_sources" ]]; then
    cat "$PWD/extra_sources"
    extra_cmds+=(-s "conf:$PWD/extra_sources")
fi

if [[ ${#DEFAULT_RPMS[@]} -gt 0 ]]; then
    extra_cmds+=($(printf -- '-l %s ' "${DEFAULT_RPMS[@]}"))
fi

if [[ -e "$CREATE_IMAGES" ]]; then
    extra_cmds+=(-i)
fi

# At first SIGTERM will be sent.
# If "run_suite.sh" will not stop, SIGKILL will be sent
# after the duration that was specified to --kill-after.
timeout \
    --kill-after 5m \
    100m \
    ./run_suite.sh \
        -o "$run_path" \
        "${extra_cmds[@]}" \
        "$SUITE" \
    || res=$?

exit $res
