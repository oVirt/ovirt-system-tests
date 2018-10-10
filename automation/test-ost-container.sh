#!/bin/bash -ex


readonly suite=basic-suite-master


cli() {
    ./run-ost-container.sh "$@"
}


cleanup() {
    cli --remove-all
}


collect_logs() {
    local run_path="deployment-${suite}"
    local dest="exported-artifacts"

    echo "suite.sh: moving artifacts"
    mkdir -p "$dest"

    mv "${run_path}/current/logs" "${dest}/lago_logs"

    find "$run_path" \
        -type f \
        -iname "*.junit.xml" \
        -exec mv {} exported-artifacts/ \;

    mv test_logs "$dest"
}


on_exit() {
    collect_logs || :
    cleanup
}

main() {
    trap on_exit EXIT
    cli --suite "$suite"
    cli --list
}

[[ "${BASH_SOURCE[0]}" == "$0" ]] && main "$@"
