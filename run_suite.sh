#!/bin/bash -e
CLI="lago"
DO_CLEANUP=false

usage () {
    echo "
Usage:

$0 SUITE [-o|--output path] [-e|--engine path] [-v|--vdsm path] [-i|--ioprocess path]

This script runs a single suite of tests (a directory of tests repo)

Positional arguments:
    SUITE
        Path to directory that contains the suite to be executed

Optional arguments:
    -o,--output PATH
        Path where the new environment will be deployed.

    -e,--engine PATH
        Path to ovirt-engine appliance iso image

    -n,--node PATH
        Path to the ovirt node squashfs iso image

"
}


env_init () {
    echo "#########################"
    local template_repo="${1:-$SUITE/template-repo.json}"
    $CLI init \
        $PREFIX \
        $SUITE/init.json \
        --template-repo-path "$template_repo"
}


env_repo_setup () {\
    echo "#########################"
    cd $PREFIX
    $CLI ovirt reposetup \
        --reposync-yum-config $SUITE/reposync-config.repo \
        --engine-dir=$ENGINE_DIR \
        $ENGINE_WITH_GWT \
        --vdsm-dir=$VDSM_DIR \
        --ioprocess-dir=$IOPROCESS_DIR
    cd -
}


env_start () {
    echo "#########################"
    cd $PREFIX
    $CLI start
    cd -
}


env_deploy () {
    echo "#########################"
    cd $PREFIX
    $CLI ovirt deploy
    cd -
}


env_run_test () {
    echo "#########################"
    local res=0
    cd $PREFIX
    $CLI ovirt runtest $1 || res=$?
    cd -
    return "$res"
}


env_collect () {
    local tests_out_dir="${1?}"
    echo "#########################"
    [[ -e "${tests_out_dir%/*}" ]] || mkdir -p "${tests_out_dir%/*}"
    cd "$PREFIX/current"
    $CLI ovirt collect --output "$tests_out_dir"
    cp -a "logs" "$tests_out_dir/lago_logs"
    cd -
}


env_cleanup() {
    echo "#########################"
    local res=0
    local uuid
    echo "======== Cleaning up"
    if [[ -e "$PREFIX" ]]; then
        echo "----------- Cleaning with lago"
        $CLI --workdir "$PREFIX" destroy --yes --all-prefixes &>/dev/null \
        || res=$?
        echo "----------- Cleaning with lago done"
    elif [[ -e "$PREFIX/uuid" ]]; then
        uid="$(cat "$PREFIX/uuid")"
        uid="${uid:0:4}"
        res=1
    else
        echo "----------- No uuid found, cleaning up any lago-generated vms"
        res=1
    fi
    if [[ "$res" != "0" ]]; then
        echo "Lago cleanup did not work (that is ok), forcing libvirt"
        env_libvirt_cleanup "${SUITE##*/}" "$uid"
    fi
    echo "======== Cleanup done"
}


env_libvirt_cleanup() {
    local suite="${1?}"
    local uid="${2}"
    local domain
    local net
    if [[ "$uid" != "" ]]; then
        local domains=($( \
            virsh -c qemu:///system list --all --name \
            | egrep "$uid*" \
        ))
        local nets=($( \
            virsh -c qemu:///system net-list --all \
            | egrep "$uid*" \
            | awk '{print $1;}' \
        ))
    else
        local domains=($( \
            virsh -c qemu:///system list --all --name \
            | egrep "[[:alnum:]]*-lago_${suite}_" \
            | egrep -v "vdsm-ovirtmgmt" \
        ))
        local nets=($( \
            virsh -c qemu:///system net-list --all \
            | egrep "[[:alnum:]]{4}-.*" \
            | egrep -v "vdsm-ovirtmgmt" \
            | awk '{print $1;}' \
        ))
    fi
    echo "----------- Cleaning libvirt"
    for domain in "${domains[@]}"; do
        virsh -c qemu:///system destroy "$domain"
    done
    for net in "${nets[@]}"; do
        virsh -c qemu:///system net-destroy "$net"
    done
    echo "----------- Cleaning libvirt Done"
}


options=$( \
    getopt \
        -o ho:e:n:c \
        --long help,output:,engine:,node:,cleanup \
        -n 'run_suite.sh' \
        -- "$@" \
)
if [[ "$?" != "0" ]]; then
    exit 1
fi
eval set -- "$options"

while true; do
    case $1 in
        -o|--output)
            PREFIX=$(realpath $2)
            shift 2
            ;;
        -n|--node)
            NODE_ISO=$(realpath $2)
            shift 2
            ;;
        -e|--engine)
            ENGINE_OVA=$(realpath $2)
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -c|--cleanup)
            DO_CLEANUP=true
            shift
            ;;
        --)
            shift
            break
            ;;
    esac
done

if [[ -z "$1" ]]; then
    echo "ERROR: no suite passed"
    usage
    exit 1
fi

export SUITE="$(realpath "$1")"
if [ -z "$PREFIX" ]; then
    export PREFIX="$PWD/deployment-${SUITE##*/}"
fi

if "$DO_CLEANUP"; then
    env_cleanup
    exit $?
fi

[[ -d "$SUITE" ]] \
|| {
    echo "Suite $SUITE not found or is not a dir"
    exit 1
}

echo "################# lago version"
lago --version
echo "#################"
echo "Running suite found in ${SUITE}"
echo "Environment will be deployed at ${PREFIX}"

rm -rf "${PREFIX}"

source "${SUITE}/control.sh"

prep_suite "$ENGINE_OVA" "$NODE_ISO"
run_suite
