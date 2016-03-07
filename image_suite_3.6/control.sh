#!/usr/bin/env bash

function add_params_to_iso {
    local node_name=$1
    local iso_src=$2
    local engine_ip="192.168.200.3"
    local install="BOOTIF=eth0 ssh_pwauth=1 adminpw=ovonFQQPIAM9o"
    local server="management_server=$engine_ip"
    local network="ip=dhcp dns=192.168.200.1"
    local storage="storage_init=/dev/vda"
    local out_dir=$(mktemp -d -p ${SUITE}/images)

    #lets fix the magick libvirt permissions reqs
    chmod 755 $out_dir
    if [[ ! -f $iso_src ]] ; then
        echo "Error  install iso not found $iso_src"
        exit 1
    fi
    chmod +x "$SUITE/utils/edit-node"
    sudo $SUITE/utils/edit-node -o "$out_dir" "$iso_src" --add-boot-param "$engine_ip $install $server $network $storage hostname=$node_name"
    out_iso=$(find "$out_dir" -mindepth 1 -maxdepth 1 -type f -name '*.iso' -print -quit)

    if [[ ! -f $out_iso ]] ; then
        echo "\n Error : iso was not generated source was = $iso_src"
        exit 1
    fi

    cp -f $out_iso ${SUITE}/images/ovirt_$node_name.iso
    rm -rf $out_dir
    echo "$SUITE/images/ovirt_$node_name.iso"

}

prep_suite () {
    #TODO: Properly parste the json to add the prefix to the virt entitites
    #      or better, https://bugzilla.redhat.com/show_bug.cgi?id=1278536
    pushd ${SUITE}/utils
    rm -rf seed.iso
    genisoimage -output seed.iso -volid cidata -joliet -rock user-data meta-data
    popd
    mkdir -p ${SUITE}/images || true
    local appliance=$1
    local node=$2
    cp -f ${appliance} ${SUITE}/images/ovirt-appliance.ova
    #build custom nodes
    echo $(add_params_to_iso "node1" ${node})
    echo $(add_params_to_iso "node2" ${node})

    local suite_name="${SUITE##*/}"
    suite_name="${suite_name//./_}"
    sed \
        -e "s,@SUITE@,${SUITE},g" \
        -e "s,\(^[[:space:]]*\)\"\(engine\)\",\1\"lago_${suite_name}_\2\",g" \
        -e "s,\(^[[:space:]]*\)\"\(host[[:digit:]]\+\)\",\1\"lago_${suite_name}_\2\",g" \
        -e "s,\(^[[:space:]]*\)\"\(lago\)\",\1\"lago_${suite_name}_\2\",g" \
        -e "s,\(^[[:space:]]*\)\"\(storage[^\"]*\)\",\1\"lago_${suite_name}_\2\",g" \
        -e "s,\"net\": \"lago\",\"net\": \"lago_${suite_name}_lago\",g" \
    < ${SUITE}/init.json.in \
    > ${SUITE}/init.json


}

run_suite () {
    env_init
    env_start
    env_deploy

    for script in $(find $SUITE/test-scenarios -type f -name '*.py' | sort); do
        echo "Running script " $(basename $script)
        env_run_test $script
        env_collect $PREFIX/test_logs/post-$(basename $script)
    done
}
