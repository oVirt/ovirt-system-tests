#!/bin/bash -e
CLI="lagocli"
DO_CLEANUP=false

if [[ -n "$ENGINE_BUILD_GWT" ]]; then
    ENGINE_WITH_GWT="--engine-with-gwt"
fi


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
        Path to ovirt-engine source that will be available in the environment

    -v,--vdsm PATH
        Path to vdsm source that will be available in the environment

    -i,--ioprocess PATH
        Path to ioprocess source that will be available in the environment
"
}


env_init () {
    $CLI init \
        $PREFIX \
        $SUITE/init.json \
        --template-repo-path $SUITE/template-repo.json
}


env_repo_setup () {
    cd $PREFIX
    $CLI ovirt reposetup \
        --reposync-yum-config $SUITE/reposync-config.repo \
        --engine-dir=$ENGINE_DIR \
        $ENGINE_WITH_GWT \
        --vdsm-dir=$VDSM_DIR \
        --ioprocess-dir=$IOPROCESS_DIR
}


env_start () {
    cd $PREFIX
    $CLI start
}


env_deploy () {
    cd $PREFIX
    $CLI ovirt deploy
}


env_run_test () {
    cd $PREFIX
    $CLI ovirt runtest $1
}


env_collect () {
    cd $PREFIX
    $CLI ovirt collect --output $1
}


env_cleanup() {
    local res=0
    echo "======== Cleaning up"
    if [[ -d "$PREFIX" ]]; then
        cd $PREFIX
        echo "----------- Cleaning with lago"
        $CLI cleanup &>/dev/null \
        || res=$?
        echo "----------- Cleaning with lago done"
    else
        res=1
    fi
    if [[ "$res" != "0" ]]; then
        echo "Lago cleanup did not work (that is ok), forcing libvirt"
        env_libvirt_cleanup "${SUITE##*/}"
    fi
    echo "======== Cleanup done"
}


env_libvirt_cleanup() {
    local suite="${1?}"
    local domain
    local net
    local domains=($( \
        virsh -c qemu:///system list --all --name \
        | egrep "[[:alnum:]]*-lago_${suite}_" \
    ))
    local nets=($( \
        virsh -c qemu:///system net-list --all \
        | egrep "[[:alnum:]]*-lago_${suite}_" \
        | awk '{print $1;}' \
    ))
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
        -o ho:v:e:i:c \
        --long help,output:,vdsm:,engine:,ioprocess:,cleanup \
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
        -v|--vdsm)
            VDSM_DIR=$(realpath $2)
            shift 2
            ;;
        -e|--engine)
            ENGINE_DIR=$(realpath $2)
            shift 2
            ;;
        -i|--ioprocess)
            IOPROCESS_DIR=$(realpath $2)
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
export PREFIX="$PWD/deployment-${SUITE##*/}"

if "$DO_CLEANUP"; then
    env_cleanup
    exit $?
fi

[[ -d "$SUITE" ]] \
|| {
    echo "Suite $SUITE not found or is not a dir"
    exit 1
}

echo "Running suite found in ${SUITE}"
echo "Environment will be deployed at ${PREFIX}"

rm -rf "${PREFIX}"

source "${SUITE}/control.sh"

prep_suite
run_suite
