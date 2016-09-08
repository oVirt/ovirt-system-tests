#!/bin/bash -xe
set -o pipefail


download_appliance(){
    local appliance_version="${1:-ovirt-4.0}"
    local appliance_distro="${2:-el7}"
    local appliance_dst_file="${3:-oVirt-Engine-Appliance-$appliance_version-$appliance_distro.ova}"
    local job_url='http://jenkins.ovirt.org/job'
    job_url+="/ovirt-appliance_${appliance_version}"
    job_url+="_build-artifacts-${appliance_distro}-x86_64"
    job_url+="/lastSuccessfulBuild/artifact/exported-artifacts"

    local appliance_image_url="$(\
        wget -O - --quiet "$job_url/" \
        | grep -o -e 'oVirt-Engine[^[:space:]"]*\.ova' \
        | head -n 1\
    )"
    echo "Downloading latest appliance image $appliance_image"
    wget -O "$appliance_dst_file" "$job_url/$appliance_image_url"
}


download_node_ng(){
    local node_version="${1:-ovirt-4.0}"
    local node_distro="${2:-el7}"
    local node_squashfs_image="${3:-oVirt-Node-$version-$engine_distro.squashfs.img}"
    local job_url='http://jenkins.ovirt.org/job'
    local squashfs_image
    job_url+="/ovirt-node-ng_${node_version}_"
    job_url+="build-artifacts-${node_distro}-x86_64"
    job_url+="/lastSuccessfulBuild/artifact/exported-artifacts"

    squashfs_image="$(\
        wget -O - --quiet "$job_url/" \
        | grep -o -e 'ovirt-node-ng[^[:space:]"]*\.squashfs\.img' \
        | sort \
        | head -n 1 \
    )"
    echo "Downloading latest squashfs image $squashfs_image"
    wget -O "$node_squashfs_image" "$job_url/$squashfs_image"
}


install_host_image() {
    local node_squashfs_image="${1?}"
    local node_version="${2?}"
    local node_image="${3?}"
    rm -rf ovirt-node-ng || true
    git clone https://gerrit.ovirt.org/ovirt-node-ng
    mv "$node_squashfs_image" ovirt-node-ng/ovirt-node-ng-image.squashfs.img
    pushd ovirt-node-ng
    git checkout ovirt-4.0
    #remove this line when node_ng get patched
    sed -i 's/--extra-args "/--wait=-1 --graphics none --extra-args "console=ttyS0 /' Makefile.am
    #build installed qcow
    ./autogen.sh
    make boot.iso
    touch ovirt-node-ng-image.squashfs.img
    #use script to cheat the TTY
    script -e -c "sudo make installed-squashfs"

    #give it a chance to finish installing
    sleep 10
    while virsh list | grep -q node; do
        sleep 1
        echo "waiting"
    done
    popd
    mv ovirt-node-ng/ovirt-node-ng-image.installed.qcow2 "$node_image"
}


generate_host_image(){
    local node_version="${1:-ovirt-4.0}"
    local node_distro="${2:-el7}"
    local node_squashfs_image="${3:-oVirt-Node-$version-$engine_distro.squashfs.img}"
    local node_image="${4:-oVirt-Node-$version-$engine_distro.qcow2}"
    [[ -e "$node_squashfs_image" ]] \
    || download_node_ng "$node_version" "$node_distro" "$node_squashfs_image"
    install_host_image "$node_squashfs_image" "$node_version" "$node_image"
}


generate_images(){
    local version="${1:-ovirt-4.0}"
    local appliance_distro="${2:-el7}"
    local appliance_image="${3:-oVirt-Engine-Appliance-$version-$appliance_distro.ova}"
    local node_distro="${4:-el7}"
    local node_squashfs_image="${5:-oVirt-Node-$version-$engine_distro.squashfs.img}"
    local node_image="${6:-oVirt-Node-$version-$engine_distro.qcow2}"
    [[ -e "$appliance_image" ]] \
    || download_appliance "$version" "$appliance_distro" "$appliance_image"
    generate_host_image \
        "$version" \
        "$host_distro" \
        "$node_squashfs_image" \
        "$node_image"
}


generate_iso_seed(){
    pushd "${suite}/utils"
    rm -rf seed.iso
    genisoimage \
        -output seed.iso \
        -volid cidata \
        -joliet \
        -rock user-data \
        meta-data
    popd
}


prep_suite(){
    local version="ovirt-4.0"
    local engine_distro="el7"
    local host_distro="el7"
    local appliance_image="${1:-oVirt-Engine-Appliance-$version-$engine_distro.ova}"
    local node_squashfs_image="${2:-oVirt-Node-$version-$engine_distro.squashfs.img}"
    local node_image="${3:-oVirt-Node-$version-$engine_distro.qcow2}"
    local suite="${SUITE?}"
    local suite_name="${suite##*/}"
    suite_name="${suite_name//./_}"
    generate_images \
        "$version" \
        "$engine_distro" "$appliance_image" \
        "$host_distro" "$node_squashfs_image" "$node_image"
    generate_iso_seed
    rm -rf "${suite}/images"
    mkdir -p "${suite}/images"
    mv -f "${appliance_image}" "${suite}/images/ovirt-appliance.ova"
    mv -f "${node_image}" "${suite}/images/ovirt-node-ng-image.installed.qcow2"
}


run_suite(){
    local suite="${SUITE?}"
    local curdir="${PWD?}"
    env_init \
        "http://templates.ovirt.org/repo/repo.metadata" \
        "$suite/LagoInitFile"
    env_start
    env_deploy

    declare test_scenarios=($(ls "$suite"/test-scenarios/*.py | sort))
    declare failed=false

    for scenario in "${test_scenarios[@]}"; do
        echo "Running test scenario ${scenario##*/}"
        env_run_test "$scenario" || failed=true
        env_collect "$curdir/test_logs/${suite##*/}/post-${scenario##*/}"
        if $failed; then
            echo "@@@@ ERROR: Failed running $scenario"
            return 1
        fi
    done
}
