#!/bin/bash -xe

# This script is meant to be run within a mock environment, using
# mock_runner.sh, from the root of the repository:
#
# $ cd repository/root
# $ mock_runner.sh -e automation/basic_vagrant_suite_master.sh


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
readonly run_suite="./run_suite_vagrant.sh"


get_run_path() {
    local ram_path="/dev/shm/ost/deployment-${SUITE}"
    local disk_path="${PWD}/deployment-${SUITE}"

    [[ -d "/dev/shm/ost" ]] && rm -rf "/dev/shm/ost"
    [[ -d "$disk_path" ]] && rm -rf "$disk_path"

    "$run_suite" -o "$ram_path" --only-verify-requirements "$SUITE" && {
        echo "$ram_path"
        return
    }

    "$run_suite" -o "$disk_path" --only-verify-requirements "$SUITE" && {
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

    if ! [[ "$OST_SKIP_CLEANUP" ]]; then
        "$run_suite" -o "$run_path" --cleanup "$SUITE"
    fi

    exit
}


setup_virt() {
    export LIBGUESTFS_BACKEND=direct
    if ! [[ -c "/dev/kvm" ]]; then
        mknod /dev/kvm c 10 232
    fi
    # Uncomment to enable verbose output
    #export LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1
}

setup_vagrant() {
    setup_vagrant_storage
    setup_vagrant_plugins
}


setup_vagrant_storage() {
    ! [[ -d "$OST_HOST_CACHE" ]] && return 0

    local vagrant_home="${OST_HOST_CACHE}/vagrant/home/${UID}"
    local pool_name="vagrant_pool_${UID}"
    local pool_path="${OST_HOST_CACHE}/vagrant/pool/${pool_name}"

    # Store VAGRANT_HOME on the host if possible
    mkdir -p "$vagrant_home" && export VAGRANT_HOME="$vagrant_home"

    # Use a libvirt pool stored in the persistent cache so backing stores
    # stick around between runs
    if mkdir -p "$pool_path"; then
        export VAGRANT_POOL="$pool_name"
        if ! virsh pool-info "$pool_name"; then
            virsh pool-create-as "$pool_name" \
                dir --target "$pool_path"
        fi
        virsh pool-refresh "$pool_name"
    fi
}


setup_vagrant_plugins() {
    local PLUGINS=(vagrant-libvirt)

    for plugin in "${PLUGINS[@]}"; do
        if ! vagrant plugin list | grep -q "^$plugin"; then
            vagrant plugin install "$plugin"
        fi
    done
}


resolve_host_cache() {
    # TODO: Change the name of the cache dir in order to avoid confusion.
    # It will require us to make sure that the new cache dir exists on the
    # CI slaves.
    local dest="/var/lib/lago"

    if [[ -d "$dest" ]]; then
        export OST_HOST_CACHE="$dest"
    fi
}


main () {
    resolve_host_cache
    setup_virt
    setup_vagrant
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

    if [[ -e "$COVERAGE_MARKER" ]]; then
        extra_cmds+=(--coverage)
    fi

    # At first SIGTERM will be sent.
    # If "run_suite.sh" will not stop, SIGKILL will be sent
    # after the duration that was specified to --kill-after.
    timeout \
        --kill-after 5m \
        180m \
        "$run_suite" \
            -o "$run_path" \
            "${extra_cmds[@]}" \
            "$SUITE" \
        || res=$?

    exit $res
}


[[ "${BASH_SOURCE[0]}" == "$0" ]] && main "$@"
