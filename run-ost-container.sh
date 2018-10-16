#!/bin/bash -ex

readonly cli=docker

usage () {
    echo "
Usage:

${0##*/} [options]

This script runs an OST container and mounts the current directory
in the container.

Optional arguments:
    -h, --help
        Show this message and exit

    --lago-data-dir PATH
        A persistent data directory for lago

    --container-version VERSION
        lago-ost container image version

    --name NAME
        A name for the newly created container

    --suite SUITE
        A suite to run inside the contatiner

    --list
        List all running OST containers

    --remove-all
        Remove all running OST containers
"
}


run() {
    local name="${1?}"
    local container_version="${2:?}"
    local lago_data_dir="${3:?}"
    local subnet_dir && subnet_dir="$(mktemp -d)"
    local container_image="lagoproject/lago-ovirt:${container_version}"

    chmod 777 "$subnet_dir"

    "$cli" run \
        -d \
        --rm \
        -v "${lago_data_dir}":/var/lib/lago \
        -v "${subnet_dir}":/var/lib/lago/subnets \
        -v "${PWD}:${PWD}" \
        --device "/dev/kvm:/dev/kvm:rw" \
        -w "$PWD" \
        --privileged \
        --name "$name" \
        "$container_image"
}


run_suite() {
    local cid="${1:?}"
    local suite="${2:?}"

    _exec "$cid" ./run_suite.sh "$suite"
}


connect() {
    local cid="${1:?}"

    _exec "$cid" /bin/bash
}

_exec() {
    local cid="${1:?}"
    local tty_flag
    shift

    tty -s && tty_flag="t"
    "$cli" exec "-i${tty_flag}" "$cid" "$@"
}


list() {
    "$cli" ps -f label=com.github.lago-project.lago-ost-plugin.version "$@"
}


remove_all() {
    local ids
    ids=($(list --format '{{.ID}}'))

    for id in "${ids[@]}"; do
        "$cli" rm -f "$id"
    done
}


main() {
    local options name cid suite
    local container_version="0.45.2"
    local lago_data_dir="/var/lib/lago"

    options=$( \
    getopt \
        -o h \
        --long help,lago-data-dir:,container-version:,name: \
        --long remove-all,list,suite: \
        -n 'run-ost-container.sh' \
        -- "$@" \
)
    if [[ "$?" != "0" ]]; then
        echo "Failed to parse command"
        exit 1
    fi
    eval set -- "$options"

    while true; do
        case $1 in
            --name)
                name="$2"
                shift 2
                ;;
           --container-version)
                container_version="$2"
                shift 2
                ;;
            --lago-data-dir)
                lago_data_dir="$2"
                shift 2
                ;;
            --list)
                list
                exit "$?"
                ;;
            --remove-all)
                remove_all
                exit "$?"
                ;;
            --suite)
                suite="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            --)
                shift
                break
                ;;
        esac
    done

    cid="$(run \
        "$name" \
        "$container_version" \
        "$lago_data_dir"
    )"

    if [[ "$suite" ]]; then
        run_suite "$cid" "$suite"
    else
        connect "$cid"
    fi
}

[[ "${BASH_SOURCE[0]}" == "$0" ]] && main "$@"
