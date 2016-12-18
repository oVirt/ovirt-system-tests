#!/bin/bash -xe
#trap read debug
# install common deps

# Project's root
PROJECT="$PWD"

#All the common folders
COMMONS=(common automation run\_suite\.sh)

#Please note: This script will work with
#any suite matching the 'standard' naming:
#must end with *-<version>
ALL_SUITES=($(ls | grep suite\-))

SUITES_TO_RUN=()

GIT=$(git show --pretty='format:' --name-only)

common_flag=0
#Check if any common file was changed
for COM in "${COMMONS[@]}"
do
	if grep -E "$COM" <<< "$GIT"; then
		SUITES_TO_RUN=(${ALL_SUITES[@]})
		common_flag=1
		break
	fi
done

#Check if any suite was changed
#Skip this part if common change was found
if [[ $common_flag -eq 0 ]]; then
	for SNAME in "${ALL_SUITES[@]}"
	do
   		if grep -E "$SNAME" <<< "$GIT"; then
        		SUITES_TO_RUN+=($SNAME)
    		fi
	done
fi

echo "Versions to run: ${SUITES_TO_RUN[@]}"

# This function will collect the logs
# of each suite to a different directory
collect_suite_logs() {
  local test_logs="$PROJECT"/exported-artifacts
  if [[ -d "$test_logs" ]]; then
      suite_logs="$PROJECT"/"$SUITE"__logs
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

# run on each version + collect its logs
for SUITE in "${SUITES_TO_RUN[@]}"
do
    echo "running tests for version $VER"
    RUN_SCRIPT=$(echo "$SUITE" | sed 's/-/_/g')
    echo "running $RUN_SCRIPT.sh"
    automation/${RUN_SCRIPT}.sh

    # collect the logs for the current suite
    collect_suite_logs
done

# collect all the suit's logs to exported-artifacts
collect_all_logs
