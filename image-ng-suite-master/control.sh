#!/bin/bash -xe
set -o pipefail


download_latest_image() {
    local job_name="$1"
    local search_for="$2"
    local image_dst="$3"

    local job_url="http://jenkins.ovirt.org/job/$job_name"
    local build_num=$(wget -qO- $job_url/lastSuccessfulBuild/buildNumber)
    local artifacts_url="$job_url/$build_num/api/json?tree=artifacts[fileName]"
    local filename=$(wget -qO- $artifacts_url | grep -Po "$search_for")
    local image_url="$job_url/$build_num/artifact/exported-artifacts/$filename"

    echo "Downloading image from $image_url"
    wget -O "$image_dst" "$image_url"
}


download_appliance(){
    local appliance_version="${1:-master}"
    local appliance_distro="${2:-el7}"
    local appliance_dst_file="${3:-oVirt-Engine-Appliance-$appliance_version-$appliance_distro.ova}"

    local job_name="ovirt-appliance_${appliance_version}"
    job_name+="_build-artifacts-${appliance_distro}-x86_64"

    local file_regex='oVirt-Engine[^[:space:]"]*\.ova'

    download_latest_image "$job_name" "$file_regex" "$appliance_dst_file"
}


download_node_ng(){
    local node_version="${1:-master}"
    local node_distro="${2:-el7}"
    local node_squashfs_image="${3:-oVirt-Node-$version-$engine_distro.squashfs.img}"

    local job_name="ovirt-node-ng_${node_version}_"
    job_name+="build-artifacts-${node_distro}-x86_64"

    local file_regex='ovirt-node-ng[^[:space:]"]*\.squashfs\.img'

    download_latest_image "$job_name" "$file_regex" "$node_squashfs_image"
}


install_host_image() {
    local node_squashfs_image="${1?}"
    local boot_iso="${2?}"
    local node_version="${3?}"
    local node_image="${4?}"
    rm -rf ovirt-node-ng || true
    git clone https://gerrit.ovirt.org/ovirt-node-ng
    mv "$node_squashfs_image" ovirt-node-ng/ovirt-node-ng-image.squashfs.img
    pushd ovirt-node-ng
    git checkout master
    #remove this line when node_ng get patched
    sed -i 's/--extra-args "/--wait=-1 --graphics none --extra-args "console=ttyS0 /' Makefile.am
    #build installed qcow
    if [[ -e "$boot_iso" ]]
        then
        ./autogen.sh --with-bootiso=$boot_iso
    else
        ./autogen.sh
        make boot.iso
    fi
    touch ovirt-node-ng-image.squashfs.img
    #use script to cheat the TTY
    script -e -c "sudo make installed-squashfs"

    #give it a chance to finish installing
    sleep 10
    while virsh list | grep -q node; do
        sleep 10
        echo "waiting"
    done
    popd
    mv ovirt-node-ng/ovirt-node-ng-image.installed.qcow2 "$node_image"
}


generate_host_image(){
    local node_version="${1:-master}"
    local node_distro="${2:-el7}"
    local node_squashfs_image="${3:-oVirt-Node-$version-$engine_distro.squashfs.img}"
    local boot_iso="${4:-boot.iso}"
    local node_image="${5:-oVirt-Node-$version-$engine_distro.qcow2}"
    [[ -e "$node_squashfs_image" ]] \
    || download_node_ng "$node_version" "$node_distro" "$node_squashfs_image"
    install_host_image "$node_squashfs_image" "$boot_iso" "$node_version" "$node_image"
}


generate_images(){
    local version="${1:-master}"
    local appliance_distro="${2:-el7}"
    local appliance_image="${3:-oVirt-Engine-Appliance-$version-$appliance_distro.ova}"
    local node_distro="${4:-el7}"
    local node_squashfs_image="${5:-oVirt-Node-$version-$engine_distro.squashfs.img}"
    local boot_iso="${6:-boot.iso}"
    local node_image="${7:-oVirt-Node-$version-$engine_distro.qcow2}"
    [[ -e "$appliance_image" ]] \
    || download_appliance "$version" "$appliance_distro" "$appliance_image"
    generate_host_image \
        "$version" \
        "$host_distro" \
        "$node_squashfs_image" \
        "$boot_iso" \
        "$node_image"
}


generate_iso_seed(){
    local suite="${SUITE?}"
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
    local version="master"
    local engine_distro="el7"
    local host_distro="el7"
    local appliance_image="${1:-oVirt-Engine-Appliance-$version-$engine_distro.ova}"
    local node_squashfs_image="${2:-oVirt-Node-$version-$engine_distro.squashfs.img}"
    local boot_iso="${3:-boot.iso}"
    local node_image="${4:-oVirt-Node-$version-$engine_distro.qcow2}"
    local suite_name="${SUITE##*/}"
    local suite="${SUITE?}"
    suite_name="${suite_name//./-}"

    sed -r \
        -e "s,__ENGINE__,lago-${suite_name}-engine,g" \
        -e "s,__NODE([0-9]+)__,lago-${suite_name}-node\1,g" \
        -e "s,__LAGO_NET__,lago-${suite_name}-lago,g" \
        -e "s,__ENGINE_ISCSI__,lago-${suite_name}-storage-iscsi,g" \
        -e "s,__ENGINE_NFS__,lago-${suite_name}-storage-nfs,g" \
    < ${SUITE}/LagoInitFile.in \
    > ${SUITE}/LagoInitFile

    generate_images \
        "$version" \
        "$engine_distro" "$appliance_image" \
        "$host_distro" "$node_squashfs_image" "$boot_iso" "$node_image"
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
