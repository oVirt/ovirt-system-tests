#!/bin/bash -xe
#trap read debug
# install common deps

# Project's root
PROJECT="$PWD"

#Array to hold all the suites
#which will be executed
SUITES_TO_RUN=$(automation/change_resolver.py)
[[ -z "$SUITES_TO_RUN" ]] && SUITES_TO_RUN="basic_suite_master"

collect_suite_logs() {
    # Each suite outputs its logs to a directory named "exported-artifacts".
    # Since "check-patch" can run multiple suites, we need to rename
    # "exported-artifacts" at the end of each suite
    # (otherwise the logs will be overridden).

    # Convert the name of "exported-artifacts" directory to $1__logs
    # $1: Suite name

    local suite_name=${1:?}
    local test_logs="${PROJECT}/exported-artifacts"

    if [[ -d "$test_logs" ]]; then
        suite_logs="${PROJECT}/${suite_name}__logs"
        # Rename the logs dir
        mv "$test_logs" "$suite_logs"
    fi
}

collect_all_logs() {
    # Collect all the log directories created by "collect_suite_logs"
    # and place them inside exported-artifacts directory.

    mkdir exported-artifacts

    find . -maxdepth 1 -name '*__logs' -print0 | xargs -r -0 mv -t exported-artifacts
    find . -maxdepth 1 -name '*.log' -print0 | xargs -r -0 mv -t exported-artifacts
    tar -czf exported-artifacts.tar.gz exported-artifacts && \
        mv exported-artifacts.tar.gz exported-artifacts
}

on_exit() {
    collect_all_logs
}

on_error() {
    echo "Error on line: $1"
    collect_suite_logs "$suite"
}


pwd

# clean old logs
if [[ -d "$PROJECT/exported-artifacts" ]]; then
    rm -rf "$PROJECT/exported-artifacts"
fi

# Trap any errors and print the line number
trap 'on_error $LINENO' SIGTERM ERR
trap 'on_exit' EXIT

echo "Suites to run:"
echo "${SUITES_TO_RUN}"

# run on each version + collect its logs
for suite in ${SUITES_TO_RUN}
do
    suite_exec_script="automation/${suite/-suite-/_suite_}.sh"
    if [[ -e "$suite_exec_script" ]]; then
        echo "running $suite_exec_script"
        ./$suite_exec_script
    else
        echo "Could not find execution script for $suite"
        exit 1
    fi

    collect_suite_logs "$suite"
done
