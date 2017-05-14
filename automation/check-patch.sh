#!/bin/bash -xe
#trap read debug
# install common deps

# Project's root
PROJECT="$PWD"

#Array to hold all the suites
#which will be executed
SUITES_TO_RUN=$(automation/change_resolver.py)

# This function will collect the logs
# of each suite to a different directory
collect_suite_logs() {
  local test_logs="$PROJECT"/exported-artifacts
  if [[ -d "$test_logs" ]]; then
    suite_logs="$PROJECT/$suite""__logs"
    # Rename the logs
    mv "$test_logs" "$suite_logs"
  fi
}

# This function will collect the logs from
# all the suites and store them in exported-artifacts,
# which later will be collected by jenkins
collect_all_logs() {
    local logs=logs
    [[ -d "$logs" ]] || mkdir $logs
    # mock_cleanup.sh collects the logs from ./logs, ./*/logs
    # The root directory is jenkins' workspace
    mv *__logs logs
    mv logs exported-artifacts
    mv *.log exported-artifacts
}

# collect the logs  on failure
on_error() {
  echo "Error on line: $1"
  collect_suite_logs
  collect_all_logs
}


pwd

# clean old logs
if [[ -d "$PROJECT/exported-artifacts" ]]; then
    rm -rf "$PROJECT/exported-artifacts"
fi

#Trap any errors and print the line number
trap 'on_error $LINENO' SIGTERM ERR

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
        tput setaf 1; echo "!!! Could not find execution script for $suite"
    fi

    # collect the logs for the current suite
    collect_suite_logs
done

# collect all the suit's logs to exported-artifacts
collect_all_logs
