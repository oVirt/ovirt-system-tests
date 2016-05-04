#!/usr/bin/env bash


prep_suite () {
    #Generate ISO seed
    pushd ${SUITE}/utils
    rm -rf seed.iso
    genisoimage -output seed.iso -volid cidata -joliet -rock user-data meta-data
    popd
    rm -rf ${SUITE}/images || true
    mkdir -p ${SUITE}/images || true
    local appliance=$1
    local node=$2
    mv -f ${appliance} ${SUITE}/images/ovirt-appliance.ova
    mv -f ${node} ${SUITE}/images/ovirt-node-ng-image.installed.qcow2
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
        echo "Running script ${script##*/}"
        env_run_test "$script"
        env_collect "$PWD/test_logs/${SUITE##*/}/post-${script##*/}"
    done
}
