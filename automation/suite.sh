#!/bin/bash -xe

# This script is meant to be run within a mock environment, using
# mock_runner.sh or chrooter, from the root of the repository:
#
# $ cd repository/root
# $ mock_runner.sh -e automation/basic_suite_4.0.sh
# or
# $ chrooter -s automation/basic_suite_4.0.sh
#
# OR
#
# on a bare metal host that has been set up with setup_for_ost.sh
# In that case it uses lagofy.sh instead of run_suite.sh

source common/helpers/python.sh

SUITE="$BASH_SOURCE"
SUITE=$(echo "$SUITE" | tr '_' '-')
# Leaving just the base dir
SUITE=${SUITE##*/}
# Remove file extension
SUITE=${SUITE%.*}

echo "Running suite: $SUITE"

if [[ "${RUNNING_IN_PSI}" == "true" ]]; then
    # $distro is passed from stdci, not a good idea to depend on it, but there's currently no other way how to choose which ost-image to use
    echo "Distro: ${distro:=el8stream}"
    { source lagofy.sh $SUITE && lago_init /usr/share/ost-images/${distro}-engine-installed.qcow2 && run_tests; } &> exported-artifacts/ost_run_tests.log
    exit $?
fi

SUITE_REAL_PATH=$(realpath "$SUITE")

# Default RPMs to install in the mock env.
# Unlike the RPMs from .packages file, this RPMs will be taken from lago's
# internal repo (assuming that we have a newer version in the internal repo).
DEFAULT_RPMS=(${OVIRT_ENGINE_SDK_PKG})

#Indicate if image creation is needed
readonly CREATE_IMAGES_FILE="$PWD/CREATE_IMAGES.marker"

# Marker for running with coverage
readonly COVERAGE_MARKER="$PWD/COVERAGE.marker"

get_run_path() {
    local disk_path="${PWD}/deployment-${SUITE}"

    [[ -d "$disk_path" ]] && rm -rf "$disk_path"

    ./run_suite.sh -o "$disk_path" --only-verify-requirements "$SUITE" && {
        echo "$disk_path"
        return
    }

    return 1
}

print_host_info() {
    echo "FS info:"
    df -h

    echo "RAM info:"
    free -h
}

cleanup() {
    local run_path="$1"

    print_host_info
    [[ -d "${run_path}/default" ]] && {
        echo "Prefix size:"
        du -h -d 1 "${run_path}/default"
    }
    [[ -d "${run_path}/default/images" ]] && {
        echo "Images Size:"
        ls -lhs "${run_path}/default/images"
    }

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

    # collect coverage reports
    [[ -d "coverage" ]] && mv coverage exported-artifacts/

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
extra_sources=""
[[ -e "$SUITE_REAL_PATH/extra_sources" ]] && extra_sources="$SUITE_REAL_PATH/extra_sources"
[[ -e "$PWD/extra_sources" ]] && extra_sources="$PWD/extra_sources"

if [[ -n ${extra_sources} ]]; then
    cat "${extra_sources}"

    while IFS= read -r repo_url
    do
        extra_cmds+=(-s "${repo_url}")
    done < "${extra_sources}"
fi

if [[ ${#DEFAULT_RPMS[@]} -gt 0 ]]; then
    extra_cmds+=($(printf -- '-l %s ' "${DEFAULT_RPMS[@]}"))
fi

if [[ -e "$CREATE_IMAGES_FILE" ]]; then
    extra_cmds+=(-i)
fi

if [[ -e "$COVERAGE_MARKER" ]]; then
    extra_cmds+=(--coverage)
fi

# At first SIGTERM will be sent.
# If "run_suite.sh" will not stop, SIGKILL will be sent
# after the duration that was specified to --kill-after.
timeout \
    --kill-after 5m \
    180m \
    ./run_suite.sh \
        -o "$run_path" \
        "${extra_cmds[@]}" \
        "$SUITE" \
    || res=$?

exit $res
